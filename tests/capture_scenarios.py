"""Capture actual app responses; no mocked routes, credentials, or edited reply text."""
import argparse
import json
from pathlib import Path
import re
from urllib.parse import urlparse

from playwright.sync_api import expect, sync_playwright


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url",required=True)
    parser.add_argument("--cases",type=Path,required=True)
    parser.add_argument("--out",type=Path,required=True)
    parser.add_argument("--chrome")
    parser.add_argument("--expected-source",choices=["qwen_lora_generated","qwen_base_generated","ollama_generated"],default="qwen_lora_generated")
    args=parser.parse_args()
    parsed=urlparse(args.url)
    if parsed.scheme not in {"http","https"} or parsed.hostname not in {"127.0.0.1","localhost","leeennn009-labeq.hf.space"}:
        raise ValueError("Expected the LABEQ public demo or a loopback test server")
    cases=json.loads(args.cases.read_text())
    args.out.mkdir(parents=True,exist_ok=False)
    goals={"أحط حدود":"أوضح حدودي","أعتذر وأصلح الموقف":"أصلح غلطتي"}
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path=args.chrome)
        try:
            for case in cases:
                if case["relation"]!="صديق":raise ValueError("These captures use the friend relationship")
                page=browser.new_page(viewport={"width":1440,"height":1060})
                page.goto(args.url,wait_until="networkidle",timeout=90000)
                if page.locator("#muteBtn").is_enabled():page.locator("#muteBtn").click()
                page.get_by_role("textbox",name="اسمك",exact=True).fill("لين")
                page.locator("#nextBtn").click()
                page.get_by_role("button",name="صديق / صديقة").click()
                page.locator("#nextBtn").click()
                page.get_by_role("button",name=re.compile(goals[case["goal"]])).click()
                page.locator("#nextBtn").click()
                page.locator("#scenarioInput").fill(case["message"])
                with page.expect_response(lambda r:r.url.endswith("/api/reply") or "/model/gradio_api/call/reply/" in r.url,timeout=180000) as pending:
                    page.locator("#analyzeBtn").click()
                response=pending.value
                if not response.ok:raise RuntimeError(f"Inference HTTP {response.status}")
                if "/model/gradio_api/" in response.url:
                    parts=response.text().split("event: complete\ndata: ")
                    if len(parts)!=2:raise RuntimeError(response.text()[:500])
                    result=json.loads(parts[1].split("\n")[0])[0]
                else:result=response.json()
                if result.get("reply_source")!=args.expected_source or result.get("router_source")!="faisal":
                    raise RuntimeError("Capture requires the declared real generation source and actual Faisal routing")
                expect(page.locator("#replyText")).to_have_text(result["reply"],timeout=15000)
                expect(page.locator("#toast")).not_to_have_class(re.compile(r"\bshow\b"),timeout=15000)
                page.screenshot(path=args.out/f"{case['id']}.png",full_page=True,animations="disabled")
                (args.out/f"{case['id']}.json").write_text(json.dumps({"url":page.url,"case":case,"response":result},ensure_ascii=False,indent=2))
                print(json.dumps({"id":case["id"],"reply":result["reply"]},ensure_ascii=False),flush=True)
                page.close()
        finally:browser.close()


if __name__=="__main__":main()
