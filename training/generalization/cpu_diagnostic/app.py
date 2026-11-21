"""Private CPU-writer diagnostic with a real, separately queued Faisal GPU router."""
import os
os.environ['HF_HUB_DISABLE_XET']='1'
import spaces
import torch
import hashlib,json,math,shutil,threading,time
from pathlib import Path
import gradio as gr
from huggingface_hub import hf_hub_download
from transformers import AutoTokenizer
from transformers import AutoModelForImageTextToText
from peft import PeftModel
from labeq_engine import FAISAL_MODEL_ID,FAISAL_SYSTEM,FAISAL_OPTIONS,make_faisal_task,infer_style_without_faisal
from llama_cpp import Llama
import llama_cpp

REPO='unsloth/Qwen3.5-35B-A3B-GGUF';REV='bc014a17be43adabd7066b7a86075ff935c6a4e2'
FILE='Qwen3.5-35B-A3B-Q4_K_M.gguf';SHA='3b46d1066bc91cc2d613e3bc22ce691dd77e6f0d33c9060690d24ce6de494375'
BASE='Qwen/Qwen3.5-35B-A3B';BASE_REV='2508b2437e382c605eb0fc52b83f5545960f6b4a'
model=tokenizer=engine=None;lock=threading.Lock()
ROUTER_REV='851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a';FAISAL_REV='38849bdac4b7850c19587f78f5fe16c38adefac1'
router_tokenizer=AutoTokenizer.from_pretrained('Qwen/Qwen3.5-4B',revision=ROUTER_REV,token=False)
router_base=AutoModelForImageTextToText.from_pretrained('Qwen/Qwen3.5-4B',revision=ROUTER_REV,dtype=torch.bfloat16,attn_implementation='eager',token=False)
router=PeftModel.from_pretrained(router_base,FAISAL_MODEL_ID,subfolder='adapter',revision=FAISAL_REV,adapter_name='faisal',is_trainable=False,torch_device='cpu',token=False).to('cuda')
router.set_adapter('faisal');router.eval()

@spaces.GPU(duration=3)
def route(payload):
    message,relation,goal=(str(payload.get(k,'')) for k in ['message','relation','goal'])
    if not message or len(message)>2000 or len(goal)>500:raise ValueError('Invalid routing request')
    task=make_faisal_task(message,relation,goal)
    inputs=router_tokenizer.apply_chat_template([{'role':'system','content':FAISAL_SYSTEM},{'role':'user','content':json.dumps(task,ensure_ascii=False,separators=(',',':'))}],tokenize=True,add_generation_prompt=True,enable_thinking=False,return_tensors='pt',return_dict=True).to('cuda')
    ids=[router_tokenizer.encode(chr(65+i),add_special_tokens=False) for i in range(len(FAISAL_OPTIONS))]
    if any(len(x)!=1 for x in ids):raise RuntimeError('Option letters must tokenize individually')
    with torch.inference_mode():scores=router(**inputs,logits_to_keep=1).logits[0,-1,[x[0] for x in ids]]
    style=FAISAL_OPTIONS[int(scores.argmax().item())][0]
    return {'style':infer_style_without_faisal(message,goal) if style=='insufficient' else style,'router_source':'rule_fallback' if style=='insufficient' else 'faisal','faisal_revision':FAISAL_REV}

def metadata():
    limits={name:Path('/sys/fs/cgroup/'+name).read_text().strip() for name in ['cpu.max','memory.max'] if Path('/sys/fs/cgroup/'+name).exists()}
    return {'backend':'llama.cpp CPU writer; n_gpu_layers=0; separate real Faisal GPU route','llama_cpp_python':llama_cpp.__version__,'model':BASE,'gguf_revision':REV,'gguf_sha256':SHA,'base_revision':BASE_REV,'loaded':model is not None,'faisal_loaded':True,'faisal_revision':FAISAL_REV,'limits':limits,'disk_free_bytes':shutil.disk_usage('/tmp').free,'cpu_count':os.cpu_count()}

def load():
    global model,tokenizer
    if model is not None:return
    print('CPU diagnostic: downloading pinned public GGUF',flush=True)
    path=hf_hub_download(REPO,FILE,revision=REV,cache_dir='/tmp/labeq-gguf-cache',token=False)
    digest=hashlib.sha256()
    with open(path,'rb') as stream:
        while block:=stream.read(64*1024*1024):digest.update(block)
    if digest.hexdigest()!=SHA:raise RuntimeError('GGUF checksum mismatch')
    quota=Path('/sys/fs/cgroup/cpu.max').read_text().split()
    threads=min(8,os.cpu_count() or 2)
    if quota[0]!='max':threads=min(threads,max(1,math.ceil(int(quota[0])/int(quota[1]))))
    tokenizer=AutoTokenizer.from_pretrained(BASE,revision=BASE_REV,token=False)
    print('CPU diagnostic: verified GGUF; loading with '+str(threads)+' CPU threads',flush=True)
    model=Llama(model_path=path,n_ctx=4096,n_batch=512,n_threads=threads,n_threads_batch=threads,n_gpu_layers=0,verbose=False)

def run(payload):
    if not isinstance(payload,dict) or not isinstance(payload.get('rows'),list) or not 1<=len(payload['rows'])<=4:raise ValueError('One to four diagnostic rows required')
    with lock:
        load();rows=[]
        for row in payload['rows']:
            start=time.monotonic();messages=row['messages']
            if len(json.dumps(messages))>24000:raise ValueError('Diagnostic prompt too long')
            prompt=tokenizer.apply_chat_template(messages,tokenize=False,add_generation_prompt=True,enable_thinking=False)
            result=model.create_completion(prompt=prompt,max_tokens=256,temperature=float(payload.get('temperature',0)),top_p=.8,top_k=20,repeat_penalty=1.0,seed=3407,stop=['<|im_end|>','<|endoftext|>'])
            choice=result['choices'][0]
            rows.append({'id':row['id'],'reply':choice['text'],'finish_reason':choice['finish_reason'],'usage':result['usage'],'seconds':time.monotonic()-start})
            print('Completed CPU diagnostic '+row['id'],flush=True)
        return {'metadata':metadata(),'rows':rows}

def run_pipeline(payload):
    global engine
    cases=payload.get('cases') if isinstance(payload,dict) else None
    if not isinstance(cases,list) or not 1<=len(cases)<=4:raise ValueError('One to four cases required')
    with lock:
        load()
        if engine is None:
            from hybrid_pipeline import HybridEngine
            engine=HybridEngine(model,tokenizer,torch,router_tokenizer,route,ROUTER_REV,FAISAL_REV)
        rows=[]
        for case in cases:
            start=time.monotonic();engine.trace=[]
            try:
                result=engine.reply(case['message'],case['relation'],case['goal'],case.get('style','تلقائي'))
                result['router_compute']=engine.router_compute
            except Exception as exc:
                result={'status':'generation_failed','error_type':type(exc).__name__}
            rows.append({'id':case['id'],'response':result,'seconds':time.monotonic()-start,'generation_trace':engine.trace})
            print('Completed CPU pipeline '+case['id'],flush=True)
        return {'metadata':metadata(),'rows':rows}

with gr.Blocks() as demo:
    data=gr.JSON();result=gr.JSON();gr.Button('CPU development check').click(run,inputs=data,outputs=result,api_name='check')
    gr.Button('Metadata').click(metadata,inputs=[],outputs=result,api_name='metadata')
    gr.Button('Faisal routing').click(route,inputs=data,outputs=result,api_name='route')
    gr.Button('Actual CPU V16 pipeline').click(run_pipeline,inputs=data,outputs=result,api_name='pipeline')
demo.queue(default_concurrency_limit=1).launch(ssr_mode=False)
