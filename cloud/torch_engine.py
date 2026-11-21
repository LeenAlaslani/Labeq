"""Transformers/PEFT model loading compatible with ZeroGPU CUDA emulation."""
import os
from pathlib import Path

from huggingface_hub import snapshot_download
from labeq_engine import FAISAL_MODEL_ID, LabeqEngine


FAISAL_REVISION = "38849bdac4b7850c19587f78f5fe16c38adefac1"
BASE_REVISION = "851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a"


class SpaceEngine(LabeqEngine):
    def __init__(self):
        repository = os.environ["LABEQ_ADAPTER_REPO"]
        revision = os.environ["LABEQ_ADAPTER_REVISION"]
        directory = snapshot_download(
            repository, revision=revision,
            allow_patterns=["adapter_config.json", "adapter_model.safetensors"],
        )
        super().__init__(Path(directory), use_faisal=True)
        label = os.getenv("LABEQ_ADAPTER_LABEL", "Saudi LoRA pilot")
        self.generator = f"Qwen3.5-4B + {label} (Transformers, bfloat16)"
        self.adapter_revision = revision
        self.base_revision = BASE_REVISION

    def load(self):
        with self.lock:
            if self.model is not None:
                return self
            import torch
            from transformers import AutoModelForImageTextToText, AutoTokenizer
            from peft import PeftModel

            base_id = "Qwen/Qwen3.5-4B"
            tokenizer = AutoTokenizer.from_pretrained(base_id,revision=BASE_REVISION)
            base = AutoModelForImageTextToText.from_pretrained(
                base_id, revision=BASE_REVISION, dtype=torch.bfloat16,
                attn_implementation="eager",
            )
            model = PeftModel.from_pretrained(
                base, str(self.adapter_dir), adapter_name="saudi", is_trainable=False,
                torch_device="cpu",
            )
            # The original decision adapter is separate from the Saudi response adapter.
            model.load_adapter(
                FAISAL_MODEL_ID, adapter_name="faisal", subfolder="adapter",
                revision=FAISAL_REVISION, is_trainable=False, torch_device="cpu",
            )
            # Native safetensors reads stay on CPU, then ZeroGPU packs ordinary CUDA transfers.
            model.to("cuda")
            model.set_adapter("saudi")
            model.eval()
            self.torch, self.model, self.processor = torch, model, tokenizer
            self.faisal_ready = True
            return self
