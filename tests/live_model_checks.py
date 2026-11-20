"""Exercise real model routing and generation through LABEQ's normal web API."""
import argparse
import json
from pathlib import Path
import time
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from model_bridge import request_payload

import httpx


SCENARIOS = [
    {
        "category": "friendship",
        "message": "صديقتي فهمت كلامي في القروب على إنه تقليل منها وأنا قصدي أسأل بس. أبي أوضح قصدي ونحل سوء الفهم.",
        "relation": "friend", "goal": "أوضح قصدي بدون اتهام ونحل سوء الفهم بهدوء",
    },
    {
        "category": "repeated-boundary",
        "message": "زميلتي كل يوم تطلب مني أكمل شغلها وأنا أتأخر في شغلي بسبب هالشي. أبي أوضح لها إن هالمساعدة ما تقدر تستمر.",
        "relation": "work", "goal": "أوضح حدودي وأوقف الطلبات اليومية بدون تجريح",
    },
    {
        "category": "family",
        "message": "أختي تتصل علي وقت مذاكرتي كثير. أبي أقول لها إني أحتاج وقت المذاكرة بدون اتصالات مع الحفاظ على الود بيننا.",
        "relation": "family", "goal": "أحط حدود لوقت المذاكرة وأحافظ على علاقتنا",
    },
    {
        "category": "workplace",
        "message": "مديري طلب تسليم التقرير بكرة وأنا باقي لي تحليل يحتاج يومين. أبي أوضح المدة الواقعية بدون ما أوعده بموعد ما أقدر عليه.",
        "relation": "work", "goal": "أتفاوض على موعد تسليم واقعي بطريقة مهنية",
    },
    {
        "category": "apology",
        "message": "نسيت موعدي مع صديقتي وخليتها تنتظر. أبي أعتذر عن نسياني وانتظارها بدون اختلاق عذر.",
        "relation": "friend", "goal": "أعتذر عن غلطتي وأوضح إني مقدرة وقتها",
    },
    {
        "category": "clarification",
        "message": "المشرفة قالت لي أرسلي الملف قريب وما حددت أي نسخة أو الموعد. أبي أسألها عن النسخة والوقت المطلوب.",
        "relation": "work", "goal": "أطلب توضيح النسخة المطلوبة وموعد التسليم",
    },
    {
        "category": "customer",
        "message": "عميلة تسأل متى نوصل طلبها وأنا ما عندي موعد مؤكد من الشحن. أبي أرد عليها بوضوح بدون ما أخترع موعد.",
        "relation": "customer", "goal": "أوضح إن الموعد غير مؤكد بدون وعد أو معلومة مخترعة",
    },
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    output = json.loads(args.output.read_text()) if args.output.exists() else []
    with httpx.Client(base_url=args.url, timeout=150) as client:
        health = client.get("/api/model-health")
        health.raise_for_status()
        assert health.json()["model_loaded"] and health.json()["faisal_loaded"], health.json()
        transport = client.get("/api/capabilities").json().get("model_transport")
        for case in SCENARIOS:
            if any(item["input"] == case for item in output):
                continue
            started = time.monotonic()
            payload = {key: value for key, value in case.items() if key != "category"}
            if transport == "gradio":
                queued = client.post("/model/gradio_api/call/reply", json={"data": [
                    request_payload(payload["message"], payload["relation"], payload["goal"])
                ]})
                queued.raise_for_status()
                event_id = queued.json()["event_id"]
                response = client.get("/model/gradio_api/call/reply/" + event_id)
                response.raise_for_status()
                complete = response.text.split("event: complete\ndata: ")
                if len(complete) != 2:
                    raise RuntimeError("Gradio generation did not complete: " + response.text[:400])
                result = json.loads(complete[1].split("\n")[0])[0]
                result.update(style=result["style_key"], mock=False)
            else:
                response = client.post("/api/reply", json=payload)
                response.raise_for_status()
                result = response.json()
            assert result["reply_source"] == "qwen_lora_generated" and result["mock"] is False
            assert result["router_source"] in {"faisal", "rule_fallback"}, result
            assert result["reply"].strip()
            output.append({
                "input": case, "result": result, "seconds": round(time.monotonic() - started, 3),
            })
            args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2))
            print(case["category"], result["style"], result["router_source"], result["review_status"], result["reply"], flush=True)


if __name__ == "__main__":
    main()
