"""Losslessly transpose a Qwen3.5 MLX LoRA into PEFT layout; never retrains."""
import argparse
import hashlib
import json
from pathlib import Path
import re

import numpy as np
from safetensors.numpy import load_file, save_file


KEY = re.compile(
    r"language_model\.model\.(layers\.\d+\.(?:mlp\.(?:down_proj|gate_proj|up_proj)"
    r"|self_attn\.(?:q_proj|k_proj|v_proj|o_proj)))\.lora_([ab])"
)


def convert(source: Path, destination: Path):
    config = json.loads((source / "adapter_config.json").read_text())
    parameters = config["lora_parameters"]
    rank, scale = parameters["rank"], parameters["scale"]
    alpha = rank * scale
    if rank < 1 or not float(alpha).is_integer() or alpha <= 0:
        raise ValueError("Unsupported rank or scaling")
    original = load_file(str(source / "adapters.safetensors"))
    pairs, converted = {}, {}
    for key, value in original.items():
        match = KEY.fullmatch(key)
        if not match or value.ndim != 2 or not np.isfinite(value).all():
            raise ValueError(f"Unexpected MLX tensor: {key}")
        path, side = match.groups()
        if value.shape[1 if side == "a" else 0] != rank:
            raise ValueError(f"Rank mismatch: {key}")
        converted[f"base_model.model.model.language_model.{path}.lora_{side.upper()}.weight"] = np.ascontiguousarray(value.T)
        pairs.setdefault(path, {})[side] = value
    if not pairs or any(set(pair) != {"a", "b"} for pair in pairs.values()):
        raise ValueError("Incomplete LoRA pairs")
    expected = {"language_model.model." + key for key in pairs}
    if set(parameters["keys"]) != expected:
        raise ValueError("Config and checkpoint modules disagree")
    # Check the actual delta with the two layout/scaling conventions.
    random = np.random.default_rng(3407)
    for key, pair in pairs.items():
        a, b = pair["a"], pair["b"]
        x = random.normal(size=(1, a.shape[0])).astype(a.dtype)
        prefix = f"base_model.model.model.language_model.{key}"
        peft_a, peft_b = (converted[prefix + f".lora_{side}.weight"] for side in ("A", "B"))
        np.testing.assert_allclose(
            (x @ a) @ b * scale, (x @ peft_a.T) @ peft_b.T * (alpha / rank),
            rtol=1e-5, atol=1e-6,
        )
    destination.mkdir(parents=True, exist_ok=False)
    save_file(converted, str(destination / "adapter_model.safetensors"))
    peft = {
        "base_model_name_or_path": "Qwen/Qwen3.5-4B", "peft_type": "LORA",
        "task_type": "CAUSAL_LM", "inference_mode": True, "bias": "none",
        "r": rank, "lora_alpha": int(alpha), "lora_dropout": 0.0,
        "target_modules": sorted({key.rsplit(".", 1)[1] for key in pairs}),
    }
    (destination / "adapter_config.json").write_text(json.dumps(peft, indent=2) + "\n")
    saved = load_file(str(destination / "adapter_model.safetensors"))
    for key, value in saved.items():
        np.testing.assert_array_equal(value, converted[key])
    manifest = {
        "source_sha256": hashlib.sha256((source / "adapters.safetensors").read_bytes()).hexdigest(),
        "peft_sha256": hashlib.sha256((destination / "adapter_model.safetensors").read_bytes()).hexdigest(),
        "tensor_count": len(saved), "rank": rank, "mlx_scale": scale,
        "peft_alpha": int(alpha), "exact_transpose_roundtrip": True,
        "sampled_delta_equivalence": True,
    }
    (destination / "conversion.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(convert(args.source, args.destination), indent=2))
