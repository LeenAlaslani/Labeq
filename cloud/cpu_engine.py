"""Pinned Qwen/Faisal CPU serving with optional real ZeroGPU acceleration.

No model choice or adapter promotion is implied by this transport. Private QA
uses local adapter files; a qualified public deployment can use the existing
private adapter repository and its already configured Hub read access.
"""
from contextlib import nullcontext
import hashlib
import json
import os
from pathlib import Path
import time

from huggingface_hub import snapshot_download
from cloud.torch_engine import BASE_REVISION,FAISAL_REVISION
from generation_limits import GenerationBudgetError
from labeq_engine import LabeqEngine,FAISAL_MODEL_ID,FAISAL_SYSTEM,FAISAL_OPTIONS,make_faisal_task,infer_style_without_faisal,finish_reply
from writing_policy import read_policy


class ConfiguredTorchEngine(LabeqEngine):
    def __init__(self,device='cpu'):
        if device not in {'cpu','cuda'}:raise ValueError('Expected CPU or CUDA')
        directory=os.getenv('LABEQ_LOCAL_ADAPTER_DIR')
        if directory:
            directory=Path(directory)
            revision=os.getenv('LABEQ_ADAPTER_REVISION','local-private-QA')
        else:
            revision=os.environ['LABEQ_ADAPTER_REVISION']
            directory=Path(snapshot_download(os.environ['LABEQ_ADAPTER_REPO'],revision=revision,
                allow_patterns=['adapter_config.json','adapter_model.safetensors']))
        for filename in ['adapter_config.json','adapter_model.safetensors']:
            if not (directory/filename).is_file():raise FileNotFoundError(filename)
        config=json.loads((directory/'adapter_config.json').read_text())
        if config.get('base_model_name_or_path') not in {'Qwen/Qwen3.5-4B','unsloth/Qwen3.5-4B'}:
            raise ValueError('This backend requires a compatible Qwen3.5-4B adapter')
        super().__init__(directory,use_faisal=True)
        self.device_name=device;self.compute_backend='torch-cpu' if device=='cpu' else 'zerogpu-cuda'
        self.adapter_revision=revision;self.base_revision=BASE_REVISION;self.faisal_revision=FAISAL_REVISION
        digest=hashlib.sha256()
        with (directory/'adapter_model.safetensors').open('rb') as stream:
            while block:=stream.read(1024*1024):digest.update(block)
        self.adapter_sha256=digest.hexdigest()
        label=os.getenv('LABEQ_ADAPTER_LABEL','Saudi pilot LoRA')
        self.generator=f'Qwen3.5-4B + {label} (Transformers, bfloat16, {device})'
        policy=os.getenv('LABEQ_WRITER_POLICY')
        if policy:self.writer_system,self.writer_examples=read_policy(policy)
        self.deadline=0

    def load(self):
        with self.lock:
            if self.model is None:
                import torch
                from transformers import AutoModelForImageTextToText,AutoTokenizer
                from peft import PeftModel
                torch.set_num_threads(8)
                tokenizer=AutoTokenizer.from_pretrained('Qwen/Qwen3.5-4B',revision=BASE_REVISION)
                base=AutoModelForImageTextToText.from_pretrained('Qwen/Qwen3.5-4B',revision=BASE_REVISION,
                    dtype=torch.bfloat16,attn_implementation='eager',device_map='cpu')
                model=PeftModel.from_pretrained(base,str(self.adapter_dir),adapter_name='saudi',is_trainable=False,torch_device='cpu')
                model.load_adapter(FAISAL_MODEL_ID,adapter_name='faisal',subfolder='adapter',revision=FAISAL_REVISION,is_trainable=False,torch_device='cpu')
                model.to(self.device_name);model.set_adapter('saudi');model.eval()
                self.torch,self.model,self.processor=torch,model,tokenizer
                self.faisal_ready=True
            # reply_v16 calls load at the start; generation never resets this budget.
            self.deadline=time.monotonic()+135
            self.generation_trace=[]
            return self

    def predict_style(self,message,relation,goal):
        self.load()
        with self.lock:
            try:
                self.model.set_adapter('faisal')
                inputs=self._inputs([{'role':'system','content':FAISAL_SYSTEM},
                    {'role':'user','content':json.dumps(make_faisal_task(message,relation,goal),ensure_ascii=False,separators=(',',':'))}])
                ids=[self.processor.encode(chr(65+i),add_special_tokens=False) for i in range(len(FAISAL_OPTIONS))]
                if any(len(x)!=1 for x in ids):raise ValueError('Faisal letters must be single tokens')
                with self.torch.inference_mode():scores=self.model(**inputs,logits_to_keep=1).logits[0,-1,[x[0] for x in ids]]
                style=FAISAL_OPTIONS[int(scores.argmax().item())][0]
                if style!='insufficient':return style,'faisal'
            except Exception as exc:self.faisal_error=type(exc).__name__
            finally:self.model.set_adapter('saudi')
        return infer_style_without_faisal(message,goal),'rule_fallback'

    def _one_generation(self,messages,retry=False,use_adapter=True,max_tokens=256):
        if self.device_name=='cuda':return super()._one_generation(messages,retry,use_adapter,max_tokens)
        with self.lock:
            remaining=self.deadline-time.monotonic()
            if remaining<=1:raise TimeoutError('CPU reply budget exhausted')
            phase_budget=45 if use_adapter else (15 if max_tokens<=256 else 30)
            self.model.set_adapter('saudi');inputs=self._inputs(messages)
            eos=self.processor.eos_token_id;stop_ids=set(eos if isinstance(eos,(list,tuple)) else [eos])
            options={'max_new_tokens':max_tokens,'max_time':min(phase_budget,remaining-1),
                'do_sample':retry,'repetition_penalty':1.08,'pad_token_id':eos,'eos_token_id':eos,'forced_eos_token_id':None}
            if retry:options.update(temperature=.45,top_p=.85)
            context=nullcontext() if use_adapter else self.model.disable_adapter()
            start=time.monotonic()
            with context,self.torch.inference_mode():outputs=self.model.generate(**inputs,**options)
            ids=outputs[0,inputs['input_ids'].shape[-1]:]
            text=finish_reply(self.processor.decode(ids,skip_special_tokens=True))
            complete=bool(len(ids)) and int(ids[-1]) in stop_ids
            self.last_generation={'generation_tokens':len(ids),'seconds':time.monotonic()-start,
                'finish_reason':'stop' if complete else 'budget','compute_backend':self.compute_backend,
                'phase':'writer' if use_adapter else ('plan' if max_tokens<=256 else 'review'),
                'max_tokens':max_tokens,'max_seconds':options['max_time'],
                'decoded_text':self.processor.decode(ids,skip_special_tokens=True)}
            self.generation_trace.append(dict(self.last_generation))
            if not complete:raise GenerationBudgetError(text)
            if not text:raise RuntimeError('CPU model returned empty text')
            return text
