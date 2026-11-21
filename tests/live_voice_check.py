"""Verify one genuine Maha reply clip, playback, and character speech state."""
import argparse
import base64
import io
import json
from pathlib import Path
import wave

from playwright.sync_api import expect, sync_playwright


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--chrome")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=args.chrome)
        page = browser.new_page(viewport={"width": 1440, "height": 960})
        page.goto(args.url, wait_until="networkidle")
        page.locator("#muteBtn").click()
        page.locator("#quickDemoBtn").click()
        with page.expect_response(lambda r: r.url.endswith("/api/reply"), timeout=150000) as pending:
            page.locator("#analyzeBtn").click()
        result = pending.value.json()
        assert result["reply_source"] == "qwen_lora_generated", result
        text = result["reply"]
        # At most one short clip, within the owner's approved 1,000-credit allowance.
        assert 0 < len(text) <= 150, "Reply exceeds the bounded live speech test"
        expect(page.locator("#voiceMetaText")).to_contain_text("منصت")
        with page.expect_response(lambda r: r.url.endswith("/api/speak"), timeout=110000) as pending:
            page.locator("#listenReplyBtn").click()
        response = pending.value
        if not response.ok:
            failure = {"provider": "munsit", "voice": "Maha - Najdi", "http_status": response.status,
                       "error": response.json(), "actual_playback": False}
            (args.out / "maha-test.json").write_text(json.dumps(failure, ensure_ascii=False, indent=2))
            raise RuntimeError(f"Maha synthesis failed: HTTP {response.status}, {response.text()}")
        speech = response.json()
        assert speech["voice"] == "Maha", speech.get("voice")
        audio = base64.b64decode(speech["audio_base64"], validate=True)
        with wave.open(io.BytesIO(audio)) as wav:
            assert wav.getframerate() == 48000
            duration = wav.getnframes() / wav.getframerate()
            assert duration > 0.2
        (args.out / "maha-generated-reply.wav").write_bytes(audio)
        expect(page.locator("#avatarWrap")).to_have_attribute("data-speaking", "true", timeout=20000)
        page.wait_for_function("state.audio && state.audio.currentTime > 0.1", timeout=20000)
        page.screenshot(path=args.out / "maha-playback.png", full_page=True)
        expect(page.locator("#avatarWrap")).to_have_attribute("data-speaking", "false", timeout=60000)
        # Simulate a provider outage after the genuine clip. No extra synthesis is billed.
        page.route("**/api/speak", lambda route: route.fulfill(status=503, json={"detail": "test outage"}))
        page.evaluate("speechCache.clear(); window.deviceSpeechCalls=0; speechSynthesis.speak=()=>deviceSpeechCalls++")
        page.locator("#listenReplyBtn").click()
        expect(page.locator("#voiceMetaText")).to_contain_text("غير متاح")
        assert page.evaluate("window.deviceSpeechCalls") == 0
        report = {
            "provider": "munsit", "voice": "Maha - Najdi", "gender": "female",
            "text_characters": len(text), "text": text,
            "duration_seconds": round(duration, 3), "sample_rate": 48000,
            "sync_mode": speech["sync_mode"],
            "alignment_characters": len(speech.get("alignment", {}).get("characters", [])),
            "actual_playback": True, "character_speech_state": True,
            "outage_test": "simulated provider failure, no browser voice fallback",
        }
        (args.out / "maha-test.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
        print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)
        browser.close()


if __name__ == "__main__":
    main()
