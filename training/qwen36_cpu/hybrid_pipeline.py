"""Development implementation of the actual V16 pipeline with an unadapted CPU writer."""
import json
from pathlib import Path
from LABEQ_V16_Coaching_Engine import reply_v16
from labeq_engine import FAISAL_MODEL_ID,FAISAL_SYSTEM,FAISAL_OPTIONS,make_faisal_task,infer_style_without_faisal,finish_reply
from generation_limits import GenerationBudgetError
from grounded_review import REVIEW_MARKER,id_review_prompt,review_schema,attach_source_quotes


class HybridEngine:
    reply_source='qwen_base_generated'
    generator='Qwen3.6-35B-A3B (GGUF Q8_0, CPU; no response adapter)'
    faisal_ready=True
    review_prompt_builder=staticmethod(id_review_prompt)

    def __init__(self,writer,tokenizer,torch,router_tokenizer,gpu_route,router_revision,faisal_revision):
        self.writer,self.tokenizer,self.torch=writer,tokenizer,torch
        self.router_tokenizer,self.gpu_route=router_tokenizer,gpu_route
        self.router_revision,self.faisal_revision=router_revision,faisal_revision
        self.cpu_router=None;self.trace=[];self.force_cpu_router=True;self.router_compute=None
        policy=json.loads(Path('writer_clean.json').read_text())
        self.writer_system,self.writer_examples=policy['system'],policy['examples']

    def load(self):return self

    def predict_style(self,message,relation,goal):
        if not self.force_cpu_router:
            try:
                result=self.gpu_route({'message':message,'relation':relation,'goal':goal})
                self.router_compute='GPU';return result['style'],result['router_source']
            except Exception:
                # CPU fallback respects GPU quota and runs the actual original adapter.
                pass
        if self.cpu_router is None:
            from transformers import AutoModelForImageTextToText
            from peft import PeftModel
            self.torch.set_num_threads(8)
            base=AutoModelForImageTextToText.from_pretrained('Qwen/Qwen3.5-4B',revision=self.router_revision,dtype=self.torch.bfloat16,attn_implementation='eager',device_map='cpu',token=False)
            self.cpu_router=PeftModel.from_pretrained(base,FAISAL_MODEL_ID,subfolder='adapter',revision=self.faisal_revision,adapter_name='faisal',is_trainable=False,torch_device='cpu',token=False).to('cpu')
            self.cpu_router.set_adapter('faisal');self.cpu_router.eval()
        messages=[{'role':'system','content':FAISAL_SYSTEM},{'role':'user','content':json.dumps(make_faisal_task(message,relation,goal),ensure_ascii=False,separators=(',',':'))}]
        inputs=self.router_tokenizer.apply_chat_template(messages,tokenize=True,add_generation_prompt=True,enable_thinking=False,return_tensors='pt',return_dict=True).to('cpu')
        ids=[self.router_tokenizer.encode(chr(65+i),add_special_tokens=False) for i in range(len(FAISAL_OPTIONS))]
        if any(len(x)!=1 for x in ids):raise RuntimeError('Faisal labels must be single tokens')
        with self.torch.inference_mode():scores=self.cpu_router(**inputs,logits_to_keep=1).logits[0,-1,[x[0] for x in ids]]
        style=FAISAL_OPTIONS[int(scores.argmax().item())][0];self.router_compute='CPU'
        return (infer_style_without_faisal(message,goal),'rule_fallback') if style=='insufficient' else (style,'faisal')

    def _one_generation(self,messages,retry=False,use_adapter=True,max_tokens=256):
        if messages[-1]['content'].startswith(REVIEW_MARKER):
            return self._review_ids(json.loads(messages[-1]['content'][len(REVIEW_MARKER):]),max_tokens)
        prompt=self.tokenizer.apply_chat_template(messages,tokenize=False,add_generation_prompt=True,enable_thinking=False)
        greedy=getattr(self,'sampler','recommended')=='greedy'
        result=self.writer.create_completion(prompt=prompt,max_tokens=max_tokens,temperature=(.45 if retry else 0) if greedy else .7,top_p=.8,top_k=20,min_p=0.0,presence_penalty=0 if greedy else 1.5,repeat_penalty=1.,seed=3407,stop=['<|im_end|>','<|endoftext|>'])
        choice=result['choices'][0];text=finish_reply(choice['text'])
        self.trace.append({'messages':messages,'text':text,'finish_reason':choice['finish_reason'],'usage':result['usage'],'max_tokens':max_tokens,'retry':retry,'sampler':getattr(self,'sampler','recommended')})
        if choice['finish_reason']=='length':raise GenerationBudgetError(text)
        return text

    def _review_ids(self,data,max_tokens):
        from llama_cpp import LlamaGrammar
        instructions=(
            'Review a candidate message against the original user source units. Every source ID must be evaluated. '
            'A factual-context unit need not be repeated, but must not be contradicted. A request unit is met only if ALL its actions and constraints are respected. '
            'Check negative constraints by obeying them, not by asking the candidate to repeat them. Keep speaker and recipient roles/genders exact. '
            'Unsupported is for exact candidate quotes asserting invented facts, excuses, intentions or commitments, not ordinary politeness. '
            'Language_issues is for exact candidate quotes with broken grammar, reversed pronouns or unnatural Saudi phrasing requiring repair. '
            'Quote only actual candidate fragments in these two lists. Use short English reasons, at most 12 words; empty reasons for met checks. '
            'Do not invent requirements. Return only the constrained JSON.'
        )
        messages=[{'role':'system','content':instructions},{'role':'user','content':json.dumps(data,ensure_ascii=False)}]
        prompt=self.tokenizer.apply_chat_template(messages,tokenize=False,add_generation_prompt=True,enable_thinking=False)
        grammar=LlamaGrammar.from_json_schema(json.dumps(review_schema(data['sources'])),verbose=False)
        result=self.writer.create_completion(prompt=prompt,max_tokens=max_tokens,temperature=0,repeat_penalty=1.,seed=3407,grammar=grammar,stop=['<|im_end|>','<|endoftext|>'])
        choice=result['choices'][0]
        self.trace.append({'phase':'source_id_review','messages':messages,'text':finish_reply(choice['text']),'usage':result['usage'],'finish_reason':choice['finish_reason'],'max_tokens':max_tokens})
        if choice['finish_reason']=='length':raise GenerationBudgetError('Incomplete structured review')
        return attach_source_quotes(choice['text'],data['sources'])

    reply=reply_v16
