"""Build a traceable experiment; synthetic references are explicitly not approved gold."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from saudi_register import SAUDI_SYSTEM


def prompt(message, relation, goal, style="عفوي"):
    return [
        {"role": "system", "content": SAUDI_SYSTEM},
        {"role": "user", "content": f"الموقف: {message}\nالعلاقة: {relation}\nالهدف: {goal}\nالأسلوب: {style}\nاكتب الرسالة للطرف الآخر، واحفظ كل الطلبات والقيود بدون اختصار يضيع المعنى."},
    ]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--approved-data", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    source = Path(__file__).parent
    synthetic = json.loads((source / "synthetic.json").read_text())["rows"]
    gold_path = args.approved_data / "train_gold_178.jsonl"
    gold = [json.loads(s) for s in gold_path.read_text().splitlines() if s.strip()]
    rows = []
    for i, row in enumerate(gold):
        fields = dict(line.split(": ", 1) for line in row["prompt"][1]["content"].splitlines() if ": " in line)
        rows.append({"prompt": prompt(fields["الموقف"], fields["العلاقة"], fields["الهدف"], fields["الأسلوب"]), "completion": row["completion"], "provenance": f"approved_completion_{i+1}; prompt_contract_updated"})
    for i, (relation, goal, message, answer) in enumerate(synthetic):
        # Weight longer compositional examples twice, explicitly recorded.
        for repeat in range(2):
            rows.append({"prompt": prompt(message, relation, goal), "completion": [{"role":"assistant", "content":answer}], "provenance":f"ai_authored_{i+1}; weight_copy_{repeat+1}"})
    tests = json.loads((source / "holdout.json").read_text())["cases"]
    train_messages = {r[2] for r in synthetic}
    train_messages.update(r["prompt"][1]["content"].splitlines()[0].removeprefix("الموقف: ") for r in rows)
    if train_messages & {r["message"] for r in tests}:
        raise ValueError("Holdout contamination")
    random.Random(3407).shuffle(rows)
    args.out.mkdir(parents=True, exist_ok=False)
    (args.out / "train.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False)+"\n" for r in rows))
    validation = args.approved_data / "validation_114.jsonl"
    (args.out / "validation.jsonl").write_bytes(validation.read_bytes())
    manifest = {
        "approved_completion_count":len(gold), "ai_authored_unique_count":len(synthetic),
        "ai_authored_weight":2, "training_rows":len(rows), "unique_training_prompts":len({json.dumps(r["prompt"],ensure_ascii=False) for r in rows}),
        "seed":3407, "no_user_regressions_in_training":True,
        "limitations":"Exact overlap check and reviewed domain separation; not a semantic leakage guarantee. All synthetic references require human review.",
        "sha256":{str(p):digest(p) for p in [gold_path, validation, source/"synthetic.json", source/"holdout.json", source/"dev.json", args.out/"train.jsonl"]},
    }
    (args.out / "manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
    print(json.dumps(manifest,ensure_ascii=False,indent=2))


if __name__ == "__main__":
    main()
