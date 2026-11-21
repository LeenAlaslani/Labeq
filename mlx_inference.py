"""Apple Silicon inference with separate, verified adapter selections."""
from contextlib import contextmanager
import json
from pathlib import Path
import re

from LABEQ_V16_Coaching_Engine import reply_v16
from labeq_engine import (
    FAISAL_OPTIONS, FAISAL_SYSTEM, finish_reply, infer_style_without_faisal, make_faisal_task,
)


PEFT_KEY = re.compile(
    r"base_model\.model\.model\.(language_model\.layers\.\d+\."
    r"(?:mlp|self_attn|linear_attn)\.\w+)\.lora_([AB])\.weight"
)


class MlxEngine:
    def __init__(self, model_path, response_dir, faisal_dir=None, adapter_label="Saudi LoRA"):
        import mlx.core as mx
        from mlx_vlm import load

        self.mx = mx
        self.model, self.processor = load(model_path)
        self.model.eval()
        self.tokenizer = self.processor.tokenizer
        self.base_layers = {}
        self.adapters = {"base": {}}
        self.adapters["saudi"] = self._adapter_layers(response_dir)
        self.faisal_ready = False
        self.generator = f"Qwen3.5-4B + {adapter_label} (MLX 4-bit)"
        if faisal_dir:
            try:
                self.adapters["faisal"] = self._adapter_layers(faisal_dir)
                self.faisal_ready = True
            except (ValueError, OSError, AttributeError, RuntimeError) as exc:
                print(f"Faisal adapter unavailable ({type(exc).__name__}): {exc}", flush=True)

    def _adapter_layers(self, directory):
        from mlx_vlm.trainer.core import get_module_by_name
        from mlx_vlm.trainer.peft.lora_layers import LoRALinear

        directory = Path(directory)
        config = json.loads((directory / "adapter_config.json").read_text())
        if config.get("peft_type") == "LORA":
            if config.get("base_model_name_or_path") not in {"Qwen/Qwen3.5-4B", "unsloth/Qwen3.5-4B"}:
                raise ValueError("Expected a Qwen3.5-4B PEFT adapter")
            if any(config.get(name) for name in (
                "use_dora", "use_rslora", "rank_pattern", "alpha_pattern", "modules_to_save"
            )):
                raise ValueError("Unsupported PEFT adapter configuration")
            rank = config["r"]
            scale = config["lora_alpha"] / rank
            weights = {}
            for key, value in self.mx.load(str(directory / "adapter_model.safetensors")).items():
                match = PEFT_KEY.fullmatch(key)
                if not match:
                    raise ValueError(f"Unexpected PEFT layer: {key}")
                path, side = match.groups()
                suffix = path.removeprefix("language_model.")
                weights[f"language_model.model.{suffix}.lora_{side.lower()}"] = value.T
        else:
            params = config["lora_parameters"]
            rank, scale = params["rank"], params["scale"]
            weights = self.mx.load(str(directory / "adapters.safetensors"))

        paths = {key.rsplit(".", 1)[0] for key in weights}
        if not paths or set(weights) != {f"{p}.lora_{side}" for p in paths for side in ("a", "b")}:
            raise ValueError("Incomplete LoRA tensor pairs")
        layers = {}
        for path in sorted(paths):
            if not path.startswith("language_model."):
                raise ValueError(f"Unexpected non-text adapter layer: {path}")
            base = get_module_by_name(self.model, path)
            layer = LoRALinear.from_base(base, r=rank, dropout=0.0, scale=scale)
            a, b = (weights[f"{path}.lora_{side}"] for side in ("a", "b"))
            if a.shape != layer.lora_a.shape or b.shape != layer.lora_b.shape:
                raise ValueError(f"LoRA dimensions do not match {path}")
            layer.lora_a, layer.lora_b = a, b
            layer.eval()
            layers[path] = layer
            self.base_layers[path] = base
        self.mx.eval(weights)
        print(f"Loaded {len(weights)} adapter tensors from {directory.name}.", flush=True)
        return layers

    @contextmanager
    def select(self, adapter):
        from mlx_vlm.trainer.core import set_module_by_name

        selected = self.adapters[adapter]
        try:
            for path, layer in selected.items():
                set_module_by_name(self.model, path, layer)
            yield
        finally:
            for path in selected:
                set_module_by_name(self.model, path, self.base_layers[path])

    def load(self):
        return self

    def predict_style(self, message, relation, goal):
        if self.faisal_ready:
            try:
                task = make_faisal_task(message, relation, goal)
                messages = [
                    {"role": "system", "content": FAISAL_SYSTEM},
                    {"role": "user", "content": json.dumps(task, ensure_ascii=False, separators=(",", ":"))},
                ]
                prompt = self.render(messages)
                ids = self.tokenizer.encode(prompt, add_special_tokens=False)
                option_ids = [
                    self.tokenizer.encode(opt["label"], add_special_tokens=False)
                    for opt in task["options"]
                ]
                if any(len(ids) != 1 for ids in option_ids):
                    raise ValueError("Faisal option letters must tokenize individually")
                with self.select("faisal"):
                    output = self.model.language_model(self.mx.array([ids]))
                    scores = output.logits[0, -1, self.mx.array([ids[0] for ids in option_ids])]
                    style = FAISAL_OPTIONS[int(self.mx.argmax(scores).item())][0]
                if style != "insufficient":
                    return style, "faisal"
            except (ValueError, RuntimeError, AttributeError) as exc:
                print(f"Faisal prediction failed ({type(exc).__name__}).", flush=True)
        return infer_style_without_faisal(message, goal), "rule_fallback"

    def render(self, messages):
        return self.tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True, enable_thinking=False,
        )

    def generate(self, messages, adapter, max_tokens=125, temperature=0.0):
        from mlx_vlm import generate

        with self.select(adapter):
            result = generate(
                self.model, self.processor, self.render(messages),
                max_tokens=max_tokens, temperature=temperature, verbose=False,
            )
        return finish_reply(result.text)

    def _one_generation(self, messages, retry=False, use_adapter=True, max_tokens=256):
        return self.generate(messages, "saudi" if use_adapter else "base", temperature=0.45 if retry else 0.0, max_tokens=max_tokens)

    reply = reply_v16
