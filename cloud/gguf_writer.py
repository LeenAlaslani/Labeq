"""Opt-in quantized CPU writing with separately verified, real Saudi LoRA files.

Original Faisal still executes on the pinned BF16 base through its existing
adapter. Only response generation uses llama.cpp and the public GGUF base.
"""
import json
import os
from pathlib import Path
import time

from cloud.cpu_engine import ConfiguredTorchEngine
from cloud.ensemble_engine import digest
from generation_limits import GenerationBudgetError
from labeq_engine import finish_reply

REPOSITORY='unsloth/Qwen3.5-4B-GGUF'
REVISION='e87f176479d0855a907a41277aca2f8ee7a09523'
FILENAME='Qwen3.5-4B-Q4_K_M.gguf'
WEIGHTS_SHA256='00fe7986ff5f6b463e62455821146049db6f9313603938a70800d1fb69ef11a4'


class ConfiguredGGUFWriter(ConfiguredTorchEngine):
    writer_runtime_label='GGUF Q4_K_M base, F32 LoRA, CPU'

    def __init__(self):
        super().__init__('cpu')
        self.contexts={};self.gguf_adapters={};self.gguf_model_path=None
        self.compute_backend='llama-cpp-cpu-lora'

    def prepare_adapter(self,name,peft_directory):
        from llama_cpp import Llama
        directory=Path(os.environ['LABEQ_GGUF_ADAPTER_DIR'])
        key='pilot' if name=='saudi' else 'v2'
        manifest=json.loads((directory/(key+'-verification.json')).read_text())
        path=directory/manifest['gguf_file']
        if not manifest.get('all_factors_exact') or manifest['tensor_count']!=256:
            raise ValueError('Unverified GGUF adapter conversion')
        if digest(Path(peft_directory)/'adapter_model.safetensors')!=manifest['peft_sha256'] or digest(path)!=manifest['gguf_sha256']:
            raise ValueError('GGUF/PEFT provenance mismatch')
        context=Llama(model_path=self.gguf_model_path,lora_path=str(path),lora_scale=1.0,
            n_ctx=4096,n_batch=512,n_threads=8,n_threads_batch=8,n_gpu_layers=0,verbose=False)
        self.contexts[name]=context;self.gguf_adapters[key]=manifest

    def load(self):
        super().load()
        if not self.contexts:
            from huggingface_hub import hf_hub_download
            path=hf_hub_download(REPOSITORY,FILENAME,revision=REVISION,token=False)
            if digest(path)!=WEIGHTS_SHA256:raise ValueError('Writer base GGUF checksum mismatch')
            self.gguf_model_path=path
            self.prepare_adapter('saudi',self.adapter_dir)
        return self

    def load_second_adapter(self,directory):
        if 'saudi_v2' not in self.contexts:self.prepare_adapter('saudi_v2',directory)

    def deployment_metadata(self):
        return {'writer_runtime':self.writer_runtime_label,'writer_gguf_repository':REPOSITORY,
                'writer_gguf_revision':REVISION,'writer_gguf_sha256':WEIGHTS_SHA256,
                'writer_gguf_adapters':self.gguf_adapters}

    def _one_generation(self,messages,retry=False,use_adapter=True,max_tokens=256):
        if not use_adapter:raise ValueError('GGUF writer requires its actual response adapter')
        from llama_cpp import StoppingCriteriaList
        deadline=min(self.deadline,time.monotonic()+getattr(self,'generation_time_limit',22))
        if time.monotonic()>=deadline-1:raise TimeoutError('Writer time budget exhausted')
        expired=[False]
        def timed_out(tokens,logits):
            expired[0]=time.monotonic()>=deadline
            return expired[0]
        prompt=self.processor.apply_chat_template(messages,tokenize=False,add_generation_prompt=True,enable_thinking=False)
        start=time.monotonic()
        result=self.contexts[getattr(self,'active_writer_adapter','saudi')].create_completion(
            prompt=prompt,max_tokens=max_tokens,temperature=.45 if retry else 0,top_p=.85,
            repeat_penalty=1.0,presence_penalty=0,seed=3407,
            stop=['<|im_end|>','<|endoftext|>'],stopping_criteria=StoppingCriteriaList([timed_out]))
        choice=result['choices'][0];raw=choice['text']
        self.last_generation={'generation_tokens':result['usage']['completion_tokens'],
            'seconds':time.monotonic()-start,'finish_reason':choice['finish_reason'],
            'timed_out':expired[0],'compute_backend':self.compute_backend,'phase':'writer',
            'max_tokens':max_tokens,'max_seconds':getattr(self,'generation_time_limit',22),'decoded_text':raw}
        self.generation_trace.append(dict(self.last_generation))
        if expired[0] or choice['finish_reason']=='length':raise GenerationBudgetError(raw)
        text=finish_reply(raw)
        if not text:raise RuntimeError('GGUF adapter returned empty text')
        return text
