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
        self.editor_model_id = os.getenv("LABEQ_EDITOR_MODEL", "").strip()
        self.editor_revision = os.getenv("LABEQ_EDITOR_REVISION", "").strip()
        self.editor_enabled = bool(self.editor_model_id)
        self.editor_model = self.editor_processor = None
        if self.editor_enabled:
            if not self.editor_revision:
                raise ValueError("Pin LABEQ_EDITOR_REVISION when enabling the editor")
            self.editor_directory = snapshot_download(
                self.editor_model_id, revision=self.editor_revision,
                allow_patterns=["*.json", "*.jinja", "*.safetensors"],
            )
            self.generator += f"; {self.editor_model_id} language editor"

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
                base_id, dtype=torch.bfloat16,
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

    def _editor_generation(self, messages):
        # Called only inside the queued GPU allocation. Streaming to CUDA keeps
        # the second model out of the Space's CPU startup working set.
        from transformers import AutoModelForImageTextToText, AutoTokenizer
        if self.editor_model is None:
            self.editor_processor = AutoTokenizer.from_pretrained(self.editor_directory)
            self.editor_model = AutoModelForImageTextToText.from_pretrained(
                self.editor_directory, dtype=self.torch.bfloat16,
                device_map={"": "cuda"}, attn_implementation="eager",
            ).eval()
        tokenizer = self.editor_processor
        inputs = tokenizer.apply_chat_template(
            messages, tokenize=True, add_generation_prompt=True, enable_thinking=False,
            return_dict=True, return_tensors="pt",
        )
        inputs = {key: value.to(self.editor_model.device) for key, value in inputs.items()}
        with self.torch.inference_mode():
            output = self.editor_model.generate(
                **inputs, max_new_tokens=180, do_sample=False, repetition_penalty=1.08,
                pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id,
            )
        from labeq_engine import finish_reply
        return finish_reply(tokenizer.decode(output[0, inputs["input_ids"].shape[-1]:], skip_special_tokens=True))

    def _one_generation(self, messages, retry=False, use_adapter=True):
        if not use_adapter and self.editor_enabled:
            return self._editor_generation(messages)
        return super()._one_generation(messages, retry=retry, use_adapter=use_adapter)

    def edit_reply(self, messages):
        return self._editor_generation(messages)
