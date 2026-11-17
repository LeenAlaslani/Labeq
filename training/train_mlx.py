"""Train the approved text-only Saudi adapter with MLX-VLM on Apple Silicon."""

import argparse
from dataclasses import asdict
from importlib.metadata import version
import json
from pathlib import Path
import platform
import random
import shutil

from validate_data import validate, read_rows


SEED = 3407
MAX_LENGTH = 768
TARGETS = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]


def prepare(rows, tok, mx):
    batches = []
    for row in rows:
        prefix = tok.apply_chat_template(
            row["prompt"], tokenize=False, add_generation_prompt=True, enable_thinking=False
        )
        prompt_ids = tok.encode(prefix, add_special_tokens=False)
        answer = row["completion"][0]["content"].strip()
        answer_ids = tok.encode(answer, add_special_tokens=False) + [tok.eos_token_id]
        ids = prompt_ids + answer_ids
        if len(ids) > MAX_LENGTH:
            raise ValueError(f"Example exceeds the {MAX_LENGTH}-token limit: {len(ids)} tokens")
        batches.append({
            "input_ids": mx.array(ids),
            "attention_mask": mx.ones(len(ids), dtype=mx.int32),
            "completion_mask": mx.array([0] * len(prompt_ids) + [1] * len(answer_ids)),
        })
    return batches


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--model", required=True, help="Local or Hub Qwen3.5-4B MLX snapshot")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--smoke", action="store_true", help="Diagnostic run on 8 train and 4 validation rows")
    args = parser.parse_args()

    validate(args.data)
    train = read_rows(args.data / "train_full_958.jsonl")
    validation = read_rows(args.data / "validation_114.jsonl")
    args.out.mkdir(parents=True, exist_ok=False)

    import mlx.core as mx
    import mlx.optimizers as optim
    import numpy as np
    from mlx_vlm import load
    from mlx_vlm.trainer.api import Trainer, task_spec
    from mlx_vlm.trainer.common.model import prepare_model_for_training

    random.seed(SEED)
    np.random.seed(SEED)
    mx.random.seed(SEED)
    model, processor = load(args.model)
    tok = processor.tokenizer
    train_data = prepare(train[:8] if args.smoke else train, tok, mx)
    val_data = prepare(validation[:4] if args.smoke else validation, tok, mx)
    model = prepare_model_for_training(model, lora_rank=16, lora_alpha=16, target_modules=TARGETS)
    _, (_, config_class) = task_spec("vlm", "sft")
    batch_size = 2
    epochs = 1 if args.smoke else 2
    iterations = epochs * (len(train_data) // batch_size)
    config = config_class(
        batch_size=batch_size,
        iters=iterations,
        gradient_accumulation_steps=1 if args.smoke else 2,
        max_seq_length=MAX_LENGTH,
        val_batches=len(val_data) // batch_size,
        steps_per_eval=iterations if args.smoke else iterations // 2,
        steps_per_save=iterations if args.smoke else 200,
        steps_per_report=1 if args.smoke else 20,
        adapter_file=str(args.out / "adapters.safetensors"),
        train_on_completions=True,
        grad_checkpoint=True,
    )
    updates = iterations // config.gradient_accumulation_steps
    warmup = max(1, round(updates * 0.05))
    schedule = optim.join_schedules(
        [optim.linear_schedule(1e-7, 5e-5, warmup), optim.cosine_decay(5e-5, max(1, updates - warmup))],
        [warmup],
    )
    trainer = Trainer(
        model, config, optimizer=optim.AdamW(schedule, weight_decay=0.0),
        train_dataset=train_data, eval_dataset=val_data,
        processing_class=processor, prepared=True, seed=SEED,
    )
    details = {
        "engine": "MLX-VLM",
        "mlx": version("mlx"),
        "mlx_vlm": version("mlx-vlm"),
        "platform": platform.platform(),
        "device": str(mx.default_device()),
        "gpu": mx.device_info(),
        "model": args.model,
        "seed": SEED,
        "mode": "smoke" if args.smoke else "full",
        "epochs": epochs,
        "train_examples": len(train_data),
        "validation_examples": len(val_data),
        "learning_rate": 5e-5,
        "optimizer_updates": updates,
        "warmup_updates": warmup,
        "target_modules": TARGETS,
        "config": asdict(config),
    }
    (args.out / "run_config.json").write_text(json.dumps(details, indent=2, default=str))
    shutil.copyfile(args.data / "dataset_manifest.json", args.out / "dataset_manifest.json")
    print(json.dumps(details, indent=2, default=str), flush=True)
    metrics = trainer.train()
    if not (args.out / "adapters.safetensors").is_file():
        raise RuntimeError("Training finished without final adapter weights")
    result = {"metrics": metrics, "validation": trainer.evaluate(), "history": trainer.log_history}
    (args.out / "metrics.json").write_text(json.dumps(result, indent=2, default=str))
    print(json.dumps(result["validation"], indent=2, default=str), flush=True)


if __name__ == "__main__":
    main()
