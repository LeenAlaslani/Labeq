"""Pinned CPU meaning planning, candidate selection and source-ID review."""
import hashlib
import json
from pathlib import Path
import time

from generation_limits import GenerationBudgetError
from grounded_review import review_schema,attach_source_quotes
from labeq_engine import FAISAL_SYSTEM
from meaning_plan import PLAN_SYSTEM,parse_plan

REPOSITORY='unsloth/Qwen3.6-35B-A3B-GGUF'
REVISION='a483e9e6cbd595906af30beda3187c2663a1118c'
FILENAME='Qwen3.6-35B-A3B-Q8_0.gguf'
WEIGHTS_SHA256='d1a395809f65a43a13ad119eb4e7acdef1ac6d68120f39902c8ab96e72794a59'
MODEL='Qwen/Qwen3.6-35B-A3B'
MODEL_REVISION='345d467b117d1fd5eda9b879a5988de9ae5f47a7'


class SemanticTeacher:
    def __init__(self):
        self.model=self.tokenizer=None;self.trace=[];self.verified=False

    def load(self):
        if self.model is not None:return self
        from huggingface_hub import hf_hub_download
        from transformers import AutoTokenizer
        from llama_cpp import Llama
        path=hf_hub_download(REPOSITORY,FILENAME,revision=REVISION,token=False)
        digest=hashlib.sha256()
        with open(path,'rb') as stream:
            while block:=stream.read(64*1024*1024):digest.update(block)
        if digest.hexdigest()!=WEIGHTS_SHA256:raise RuntimeError('Semantic model checksum mismatch')
        self.tokenizer=AutoTokenizer.from_pretrained(MODEL,revision=MODEL_REVISION,token=False)
        self.model=Llama(model_path=path,n_ctx=4096,n_batch=512,n_threads=8,n_threads_batch=8,n_gpu_layers=0,verbose=False)
        self.verified=True;return self

    def generate(self,messages,max_tokens,deadline,phase,grammar_schema=None):
        if time.monotonic()>=deadline:raise TimeoutError('Reply time budget exhausted')
        from llama_cpp import StoppingCriteriaList,LlamaGrammar
        expired=[False]
        def timed_out(tokens,logits):
            expired[0]=time.monotonic()>=deadline
            return expired[0]
        prompt=self.tokenizer.apply_chat_template(messages,tokenize=False,add_generation_prompt=True,enable_thinking=False)
        options={}
        if grammar_schema is not None:options['grammar']=LlamaGrammar.from_json_schema(json.dumps(grammar_schema),verbose=False)
        start=time.monotonic()
        result=self.model.create_completion(prompt=prompt,max_tokens=max_tokens,temperature=0,
            presence_penalty=0,repeat_penalty=1,seed=3407,stop=['<|im_end|>','<|endoftext|>'],
            stopping_criteria=StoppingCriteriaList([timed_out]),**options)
        choice=result['choices'][0];raw=choice['text']
        self.trace.append({'phase':phase,'messages':messages,'decoded_text':raw,'finish_reason':choice['finish_reason'],
            'timed_out':expired[0],'seconds':time.monotonic()-start,'usage':result['usage'],'max_tokens':max_tokens})
        if expired[0] or choice['finish_reason']=='length':raise GenerationBudgetError(raw)
        if not raw.strip():raise RuntimeError('Semantic model returned empty text')
        return raw

    def plan(self,case,deadline):
        messages=[{'role':'system','content':PLAN_SYSTEM},{'role':'user','content':json.dumps(case,ensure_ascii=False)}]
        return parse_plan(self.generate(messages,256,deadline,'meaning_plan'))

    def select(self,task,deadline):
        messages=[{'role':'system','content':FAISAL_SYSTEM},{'role':'user','content':json.dumps(task,ensure_ascii=False,separators=(',',':'))}]
        label=self.generate(messages,256,deadline,'candidate_selection').strip()
        if label not in {option['label'] for option in task['options']}:raise ValueError('Malformed model selection')
        return label

    def review(self,data,deadline):
        instructions=(
            'Review a candidate message against the original user source units. Every source ID must be evaluated. '
            'A factual-context unit need not be repeated, but must not be contradicted. A request unit is met only if ALL its actions and constraints are respected. '
            'Check negative constraints by obeying them, not by asking the candidate to repeat them. Keep speaker and recipient roles/genders exact. '
            'Unsupported is for exact candidate quotes asserting invented facts, excuses, intentions or commitments, not ordinary politeness. '
            'Language_issues is for exact candidate quotes with broken grammar, reversed pronouns or unnatural Saudi phrasing requiring repair. '
            'Quote only actual candidate fragments in these two lists. Use short English reasons, at most 12 words; empty reasons for met checks. '
            'Do not invent requirements. Return only the constrained JSON.'
        )
        raw=self.generate([{'role':'system','content':instructions},{'role':'user','content':json.dumps(data,ensure_ascii=False)}],640,deadline,'source_id_review',review_schema(data['sources']))
        return attach_source_quotes(raw,data['sources'])
