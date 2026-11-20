"""Transformers/PEFT model loading compatible with ZeroGPU CUDA emulation."""
import os
from pathlib import Path

from huggingface_hub import snapshot_download
from labeq_engine import FAISAL_MODEL_ID, LabeqEngine


FAISAL_REVISION = "38849bdac4b7850c19587f78f5fe16c38adefac1"


class SpaceEngine(LabeqEngine):
    def __init__(self):
        repository = os.environ["LABEQ_ADAPTER_REPO"]
        revision = os.environ["LABEQ_ADAPTER_REVISION"]
        directory = snapshot_download(
            repository, revision=revision,
            allow_patterns=["adapter_config.json", "adapter_model.safetensors"],
        )
        super().__init__(Path(directory), use_faisal=True)
        self.generator = "Qwen3.5-4B + Saudi LoRA pilot (Transformers, bfloat16)"
        self.adapter_revision = revision

    def load(self):
        with self.lock:
            if self.model is not None:
                return self
            import torch
            from transformers import AutoModelForImageTextToText, AutoTokenizer
            from peft import PeftModel

            base_id = "Qwen/Qwen3.5-4B"
            tokenizer = AutoTokenizer.from_pretrained(base_id)
            base = AutoModelForImageTextToText.from_pretrained(
                base_id, dtype=torch.bfloat16, device_map="cuda",
                attn_implementation="eager",
            )
            model = PeftModel.from_pretrained(
                base, str(self.adapter_dir), adapter_name="saudi", is_trainable=False,
            )
            # The original decision adapter is separate from the Saudi response adapter.
            model.load_adapter(
                FAISAL_MODEL_ID, adapter_name="faisal", subfolder="adapter",
                revision=FAISAL_REVISION, is_trainable=False,
            )
            model.set_adapter("saudi")
            model.eval()
            self.torch, self.model, self.processor = torch, model, tokenizer
            self.faisal_ready = True
            return self
