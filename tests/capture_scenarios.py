"""Capture actual app responses; no mocked routes, credentials, or edited reply text."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import time
from urllib.parse import urlparse

from playwright.sync_api import expect, sync_playwright


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url",required=True)
    parser.add_argument("--cases",type=Path,required=True)
    parser.add_argument("--out",type=Path,required=True)
    parser.add_argument("--chrome")
    parser.add_argument("--mobile",action="store_true")
    parser.add_argument("--expected-source",choices=["qwen_lora_generated","qwen_base_generated","ollama_generated"],default="qwen_lora_generated")
    parser.add_argument("--allow-rule-fallback",action="store_true",help="Record an explicitly labeled real routing fallback")
    args=parser.parse_args()
    parsed=urlparse(args.url)
    if parsed.scheme not in {"http","https"} or parsed.hostname not in {"127.0.0.1","localhost","leeennn009-labeq.hf.space"}:
        raise ValueError("Expected the LABEQ public demo or a loopback test server")
    cases=json.loads(args.cases.read_text())
    args.out.mkdir(parents=True,exist_ok=False)
    goals={"أحط حدود":"أوضح حدودي","أعتذر وأصلح الموقف":"أصلح غلطتي"}
    relations={'صديق':'صديق / صديقة','صديقة':'صديق / صديقة','عائلة':'أحد من العائلة','أهل':'أحد من العائلة','عمل':'زميل / مدير','عميل':'عميل'}
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path=args.chrome)
        try:
            for case in cases:
                if case['relation'] not in relations:raise ValueError('Unsupported capture relationship')
                page=browser.new_page(viewport={"width":390,"height":844} if args.mobile else {"width":1440,"height":1060},is_mobile=args.mobile)
                page.goto(args.url,wait_until="networkidle",timeout=90000)
                # Observe the original queued client's return value. Chrome may
                # discard an SSE response body after the application cancels its
                # completed reader; reading it through CDP then becomes racy.
                # This observer changes no request, response or displayed text.
                page.evaluate("""() => {
                  const original=window.labeqSpaceReply;
                  window.__labeqCapture=null;window.__labeqCaptureError=null;
                  if(typeof original==='function')window.labeqSpaceReply=async function(...args){
                    try{const result=await original.apply(this,args);window.__labeqCapture=result;return result}
                    catch(error){window.__labeqCaptureError=String(error.message);throw error}
                  };
                }""")
                if page.locator("#muteBtn").is_enabled():page.locator("#muteBtn").click()
                page.get_by_role("textbox",name="اسمك",exact=True).fill("لين")
                page.locator("#nextBtn").click()
                page.get_by_role("button",name=relations[case['relation']]).click()
                page.locator("#nextBtn").click()
                page.get_by_role("button",name=re.compile(goals.get(case["goal"],case["goal"]))).click()
                page.locator("#nextBtn").click()
                page.locator("#scenarioInput").fill(case["message"])
                started=time.monotonic()
                with page.expect_request(lambda r:r.method=='POST' and (r.url.endswith('/api/reply') or r.url.endswith('/model/gradio_api/call/reply')),timeout=180000) as submitted, page.expect_response(lambda r:r.url.endswith("/api/reply") or "/model/gradio_api/call/reply/" in r.url,timeout=180000) as pending:
                    page.locator("#analyzeBtn").click()
                response=pending.value
                if not response.ok:raise RuntimeError(f"Inference HTTP {response.status}")
                if "/model/gradio_api/" in response.url:
                    page.wait_for_function('window.__labeqCapture!==null || window.__labeqCaptureError!==null',timeout=180000)
                    error=page.evaluate('window.__labeqCaptureError')
                    if error:
                        page.screenshot(path=args.out/f"{case['id']}-error.png",full_page=True,animations='disabled')
                        raise RuntimeError('Actual queued inference failed: '+error)
                    result=page.evaluate('window.__labeqCapture')
                else:result=response.json()
                request_seconds=time.monotonic()-started
                routes={'faisal','rule_fallback'} if args.allow_rule_fallback else {'faisal'}
                if result.get("reply_source")!=args.expected_source or result.get("router_source") not in routes:
                    raise RuntimeError("Capture requires the declared real generation source and actual Faisal routing")
                expect(page.locator("#replyText")).to_have_text(result["reply"],timeout=15000)
                if page.evaluate('document.documentElement.scrollWidth>window.innerWidth'):raise RuntimeError('Horizontal layout overflow')
                expect(page.locator("#toast")).not_to_have_class(re.compile(r"\bshow\b"),timeout=15000)
                page.screenshot(path=args.out/f"{case['id']}.png",full_page=True,animations="disabled")
                (args.out/f"{case['id']}.json").write_text(json.dumps({"observed_at_utc":datetime.now(timezone.utc).isoformat(),"url":page.url,"viewport":page.viewport_size,"case":case,"request_wall_seconds":request_seconds,"capture_method":"Observed original queued client return" if '/model/gradio_api/' in response.url else 'HTTP JSON response',"actual_frontend_request":submitted.value.post_data_json,"response":result},ensure_ascii=False,indent=2))
                print(json.dumps({"id":case["id"],"reply":result["reply"]},ensure_ascii=False),flush=True)
                page.close()
        finally:browser.close()


if __name__=="__main__":main()
