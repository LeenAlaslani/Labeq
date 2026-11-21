"""Exercise the live LABEQ app in Chromium, with optional screenshot capture."""
import argparse
from pathlib import Path
import re

from playwright.sync_api import expect, sync_playwright


SITUATION = "صديقتي فهمت رسالتي غلط وزعلت مني. ودي نتفاهم بهدوء ونسمع بعض."


def capture(page, directory, name):
    if directory:
        expect(page.locator("#toast")).not_to_have_class(re.compile(r"\bshow\b"))
        page.screenshot(path=directory / f"release-{name}.png", full_page=True, animations="disabled")


def onboard(page, screenshots=None):
    expect(page.locator("html")).to_have_attribute("dir", "rtl")
    expect(page.locator("#nextBtn")).to_be_disabled()
    # Disable automatic playback while keeping voice actions available.
    if page.locator("#muteBtn").is_enabled():
        page.locator("#muteBtn").click()
    capture(page, screenshots, "onboarding")
    page.get_by_role("textbox", name="اسمك", exact=True).fill("لين")
    page.locator("#nextBtn").click()
    page.get_by_role("button", name="صديق / صديقة").click()
    capture(page, screenshots, "relationship")
    page.locator("#nextBtn").click()
    page.get_by_role("button", name=re.compile("ننهي الخلاف")).click()
    capture(page, screenshots, "goal")
    page.locator("#nextBtn").click()
    page.locator("#scenarioInput").fill(SITUATION)
    capture(page, screenshots, "situation")


def model_response(response):
    if "/model/gradio_api/call/reply/" in response.url:
        import json
        text = response.text()
        completed = text.split("event: complete\ndata: ")
        assert len(completed) == 2, text
        result = json.loads(completed[1].split("\n")[0])[0]
        return {**result, "style": result["style_key"], "mock": False}
    return response.json()


def real_flow(page, screenshots):
    onboard(page, screenshots)
    expect(page.locator("#dataBadge")).to_contain_text("Qwen", timeout=20000)
    with page.expect_response(lambda res: res.url.endswith("/api/reply") or "/model/gradio_api/call/reply/" in res.url, timeout=160000) as pending:
        page.locator("#analyzeBtn").click()
    response = pending.value
    assert response.ok, response.text()
    payload = model_response(response)
    assert payload["router_source"] == "faisal", payload
    assert payload["reply_source"] == "qwen_lora_generated" and not payload["mock"], payload
    chosen = page.locator("#replyText")
    expect(chosen).to_have_text(payload["reply"])
    capture(page, screenshots, "generated-reply")
    page.locator("#copyBtn").click()
    expect(page.locator("#toast")).to_contain_text("تم نسخ الرد")
    assert page.evaluate("navigator.clipboard.readText()") == payload["reply"]

    page.locator("#coachInsight > summary").click()
    expect(page.locator("#coachWhy")).not_to_be_empty()
    capture(page, screenshots, "coaching")

    page.locator("#replyOptions > summary").click()
    page.locator("#changeStyleBtn").click()
    style = "طلب توضيح" if payload["style"] != "clarify" else "دبلوماسي"
    with page.expect_response(lambda res: res.url.endswith("/api/reply") or "/model/gradio_api/call/reply/" in res.url, timeout=160000) as pending:
        page.locator("#styleChoices").get_by_role("button", name=style, exact=True).click()
    response = pending.value
    assert response.ok, response.text()
    second = model_response(response)
    assert second["reply"] != payload["reply"] and second["router_source"] == "user_selected", second
    expect(chosen).to_have_text(second["reply"])
    page.locator("#coachCompare > summary").click()
    expect(page.locator("#coachCompareCards .coach-comparison-card")).to_have_count(2)
    capture(page, screenshots, "style-comparison")
    print(f"Real browser requests: {payload['style']} → {second['style']}, {payload['generator']}")


def demo_flow(page, screenshots):
    external_api = []
    page.on("request", lambda request: external_api.append(request.url) if "/api/" in request.url else None)
    onboard(page)
    page.locator("#analyzeBtn").click()
    expect(page.locator("#dataBadge")).to_contain_text("نسخة عرض")
    first = page.locator("#replyText").inner_text()
    assert first
    page.locator("#replyOptions > summary").click()
    page.locator("#changeStyleBtn").click()
    page.locator("#styleChoices").get_by_role("button", name="حازم", exact=True).click()
    expect(page.locator("#replyText")).not_to_have_text(first)
    assert not external_api
    expect(page.locator("#filledResult")).to_be_visible()
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    capture(page, screenshots, "mobile-demo")
    page.evaluate("""() => {
        window.testSpokenText = null;
        window.SpeechSynthesisUtterance = class {
            constructor(text) { this.text = text; }
        };
        Object.defineProperty(window, 'speechSynthesis', {
            configurable: true,
            value: {
                getVoices: () => [{ name: 'Test Arabic voice', lang: 'ar-SA' }],
                cancel: () => {},
                speak: utterance => {
                    window.testSpokenText = utterance.text;
                    utterance.onstart();
                    setTimeout(() => utterance.onend(), 200);
                }
            }
        });
        window.SpeechRecognition = class {
            start() {
                queueMicrotask(() => {
                    this.onresult({results: [[{transcript: 'ونسمع وجهات نظر بعض'}]]});
                    this.onend();
                });
            }
        };
    }""")
    expect(page.locator("#listenReplyBtn")).to_be_disabled()
    expect(page.locator("#voiceMetaText")).to_contain_text("صوت مها غير متاح")
    assert page.evaluate("window.testSpokenText") is None
    page.locator("#editScenarioBtn").click()
    page.locator("#micBtn").click()
    expect(page.locator("#scenarioInput")).to_have_value(re.compile("ونسمع وجهات نظر بعض"))
    assert not external_api


def duplicate_variant_flow(page, url):
    """Verify the app keeps the reply and its style when a rewrite repeats it."""
    fixture = {
        "reply": "ودي نسمع بعض ونتفاهم بهدوء على اللي صار.",
        "reply_source": "qwen_lora_generated",
        "mock": False,
    }

    def model_route(route):
        payload = route.request.post_data_json
        # Resolving a disagreement must not invent "misunderstanding" as its cause.
        assert payload['goal']=='ننهي الخلاف ونتفاهم بهدوء'
        style = payload["style_key"]
        route.fulfill(json={
            **fixture, "style": style or "diplomatic",
            "router_source": "user_selected" if style else "faisal",
        })

    page.route("**/api/reply", model_route)
    page.goto(url, wait_until="networkidle")
    onboard(page)
    page.locator("#analyzeBtn").click()
    expect(page.locator("#replyText")).to_have_text(fixture["reply"])
    expect(page.locator("#stylePill")).to_have_text("دبلوماسي")
    page.locator("#replyOptions > summary").click()
    page.locator("#changeStyleBtn").click()
    page.locator("#styleChoices").get_by_role("button", name="حازم", exact=True).click()
    expect(page.locator("#toast")).to_contain_text("الصياغة قريبة من الرد السابق")
    expect(page.locator("#stylePill")).to_have_text("دبلوماسي")
    expect(page.locator("#replyText")).to_have_text(fixture["reply"])
    print("Duplicate style rewrite was rejected in the browser fixture test.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--real")
    parser.add_argument("--demo", required=True)
    parser.add_argument("--mock-web", help="Test duplicate rewrite handling against this FastAPI web URL")
    parser.add_argument("--chrome")
    parser.add_argument("--screenshots", type=Path)
    args = parser.parse_args()
    if args.screenshots:
        args.screenshots.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=args.chrome)
        if args.real:
            desktop = browser.new_context(viewport={"width": 1440, "height": 960},
                                          permissions=["clipboard-read", "clipboard-write"])
            page = desktop.new_page()
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(args.real, wait_until="networkidle")
            real_flow(page, args.screenshots)
            assert not errors, errors
            desktop.close()
        if args.mock_web:
            page = browser.new_page()
            duplicate_variant_flow(page, args.mock_web)
            page.close()
        mobile = browser.new_context(**playwright.devices["iPhone 13"])
        page = mobile.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(args.demo, wait_until="networkidle")
        demo_flow(page, args.screenshots)
        assert not errors, errors
        if args.real:
            page = mobile.new_page()
            page.goto(args.real, wait_until="networkidle")
            onboard(page)
            with page.expect_response(lambda res: "/model/gradio_api/call/reply/" in res.url or res.url.endswith("/api/reply"), timeout=160000) as pending:
                page.locator("#analyzeBtn").click()
            payload = model_response(pending.value)
            assert payload["reply_source"] == "qwen_lora_generated" and payload["router_source"] == "faisal", payload
            expect(page.locator("#replyText")).to_have_text(payload["reply"])
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            expect(page.locator("#listenReplyBtn")).to_be_disabled()
            capture(page, args.screenshots, "mobile-public")
            print("Public mobile inference and inactive Maha controls passed.")
        print("Browser smoke passed for", "desktop real inference and mobile demo" if args.real else "mobile demo")


if __name__ == "__main__":
    main()
