"""Verify the approved splits without printing training examples."""
import argparse
from collections import Counter
import json
from pathlib import Path
import unicodedata


COUNTS = {
    "train_full_958": 958,
    "train_gold_178": 178,
    "validation_114": 114,
    "test_114": 114,
    "test_38_one_per_scenario": 38,
}


def read_rows(path):
    with path.open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def fields(row):
    lines = row["prompt"][1]["content"].splitlines()
    return dict(line.split(": ", 1) for line in lines if ": " in line)


def normalized(text):
    return " ".join(unicodedata.normalize("NFKC", text).split()).casefold()


def validate(root):
    data = {}
    for name, count in COUNTS.items():
        rows = read_rows(root / f"{name}.jsonl")
        if len(rows) != count:
            raise ValueError(f"{name}: expected {count}, found {len(rows)}")
        for row in rows:
            messages = row["prompt"] + row["completion"]
            if [message["role"] for message in messages] != ["system", "user", "assistant"]:
                raise ValueError(f"{name}: invalid chat roles")
            if any(not message["content"].strip() for message in messages):
                raise ValueError(f"{name}: empty content")
        unique = {normalized(row["prompt"][1]["content"]) for row in rows}
        if len(unique) != len(rows):
            raise ValueError(f"{name}: duplicate prompts")
        data[name] = rows

    train, validation, test, sample = (data[key] for key in (
        "train_full_958", "validation_114", "test_114", "test_38_one_per_scenario"
    ))
    scenario_sets = [{normalized(fields(row)["الموقف"]) for row in rows} for rows in (train, validation, test)]
    for left, right in ((0, 1), (0, 2), (1, 2)):
        if scenario_sets[left] & scenario_sets[right]:
            raise ValueError("Scenario overlap between train, validation and test")
    if not all(row in train for row in data["train_gold_178"]):
        raise ValueError("Gold records must belong to the full train set")
    if not all(row in test for row in sample) or len({fields(row)["الموقف"] for row in sample}) != len(sample):
        raise ValueError("The 38-case evaluation must contain one row per held-out scenario")
    manifest = json.loads((root / "dataset_manifest.json").read_text(encoding="utf-8"))
    styles = Counter(fields(row)["الأسلوب"] for row in train)
    if dict(styles) != manifest["styles"]:
        raise ValueError("Training style distribution differs from dataset manifest")
    print(json.dumps({"counts": COUNTS, "train_styles": styles}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("data", type=Path)
    validate(parser.parse_args().data)
