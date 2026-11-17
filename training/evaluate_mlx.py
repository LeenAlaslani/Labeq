"""Generate paired held-out responses and a blinded human-review sheet."""
import argparse
from collections import Counter
import csv
import json
from pathlib import Path
import random
import re
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from labeq_engine import quality_flags
from mlx_inference import MlxEngine
from validate_data import fields, read_rows, validate


MODELS = ("base", "pilot", "v2")
CHECKS = {
    "non_arabic_or_empty": re.compile("[\u0600-\u06ff]"),
    "repeated_request": re.compile(r"كل\s*(?:يوم|مر[ةه]|أسبوع|اسبوع)|دايم|باستمرار|متكرر|تتكرر|يتكرر"),
    "instruction_or_trace": re.compile(r"<think>|</think>|(?:الرد المقترح|بإمكانك|تقدرين)\s*[:：]|assistant\s*:", re.I),
}


def grade_automatic(reply, row):
    context = fields(row)
    situation, goal = context["الموقف"], context["الهدف"]
    flags = quality_flags(reply, context["العلاقة"], goal, situation)
    if not CHECKS["non_arabic_or_empty"].search(reply):
        flags.append("empty_or_no_arabic")
    if CHECKS["instruction_or_trace"].search(reply):
        flags.append("instruction_or_trace")
    if CHECKS["repeated_request"].search(situation) and re.search(r"حدود|أرفض|الاعتذار عن", goal):
        if not CHECKS["repeated_request"].search(reply):
            flags.append("recurrence_phrase_missing")
    return list(dict.fromkeys(flags))


def write_report(output, cases):
    variants = [name for name in MODELS if name in cases[0]["outputs"]]
    summary = {}
    for variant in variants:
        responses = [case["outputs"][variant] for case in cases]
        counts = Counter(flag for response in responses for flag in response["flags"])
        summary[variant] = {
            "case_count": len(responses),
            "flagged_cases": sum(bool(response["flags"]) for response in responses),
            "flags": dict(counts),
            "mean_seconds": round(sum(response["seconds"] for response in responses) / len(responses), 2),
        }
    if len(variants) > 1:
        summary["identical_text"] = {
            f"{left}_{right}": sum(
                case["outputs"][left]["reply"] == case["outputs"][right]["reply"] for case in cases
            )
            for index, left in enumerate(variants) for right in variants[index + 1:]
        }
    (output / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    randomizer = random.Random(3407)
    keys = []
    with (output / "blind_review.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow((
            "case", "candidate", "situation", "relationship", "goal", "style", "response",
            "intent_1_5", "dialect_1_5", "social_fit_1_5", "goal_completion_1_5",
            "relationship_fit_1_5", "style_fit_1_5", "factuality_1_5", "usefulness_1_5", "sendable_1_5",
        ))
        for case in cases:
            order = variants.copy()
            randomizer.shuffle(order)
            ctx = case["context"]
            for i, name in enumerate(order, 1):
                writer.writerow((
                    case["case"], i, ctx["الموقف"], ctx["العلاقة"], ctx["الهدف"],
                    ctx["الأسلوب"], case["outputs"][name]["reply"], *[""] * 9,
                ))
                keys.append({"case": case["case"], "candidate": i, "model": name})
    (output / "blind_review_key.json").write_text(json.dumps(keys, indent=2))
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--pilot", type=Path, required=True)
    parser.add_argument("--v2", type=Path)
    parser.add_argument("--split", choices=[38, 114], type=int, default=38)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    validate(args.data)
    source = "test_38_one_per_scenario.jsonl" if args.split == 38 else "test_114.jsonl"
    rows = read_rows(args.data / source)
    engine = MlxEngine(args.model, args.pilot)
    adapters = {"base": "base", "pilot": "saudi"}
    if args.v2:
        engine.adapters["v2"] = engine._adapter_layers(args.v2)
        adapters["v2"] = "v2"

    args.out.mkdir(parents=True, exist_ok=True)
    results_file = args.out / "responses.jsonl"
    results = read_rows(results_file) if results_file.exists() else []
    for index, row in enumerate(rows, 1):
        case = results[index - 1] if index <= len(results) else {
            "case": index, "context": fields(row), "outputs": {},
        }
        if case["context"] != fields(row):
            raise ValueError(f"Previously written case {index} differs from the chosen data split")
        for name, key in adapters.items():
            if name not in case["outputs"]:
                start = time.monotonic()
                reply = engine.generate(row["prompt"], key, max_tokens=160, temperature=0.0)
                case["outputs"][name] = {
                    "reply": reply, "flags": grade_automatic(reply, row),
                    "seconds": round(time.monotonic() - start, 3),
                }
        if index > len(results):
            results.append(case)
        temporary = results_file.with_suffix(".tmp")
        temporary.write_text("".join(json.dumps(result, ensure_ascii=False) + "\n" for result in results))
        temporary.replace(results_file)
        print(f"Completed {index}/{len(rows)} for {', '.join(adapters)}", flush=True)
    write_report(args.out, results)


if __name__ == "__main__":
    main()
