"""Record real raw or end-to-end outputs, with pinned local-model and policy identities."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
from types import SimpleNamespace
from urllib.request import urlopen

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from ollama_inference import GenerationBudgetError, OllamaEngine
from saudi_register import SAUDI_SYSTEM
from training.generalization.build import prompt


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--model',required=True)
    p.add_argument('--policy',type=Path)
    p.add_argument('--cases',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--pipeline',action='store_true')
    p.add_argument('--faisal-model')
    p.add_argument('--faisal',type=Path)
    args=p.parse_args()
    cases=json.loads(args.cases.read_text())
    if isinstance(cases,dict):cases=cases['cases']
    router=SimpleNamespace(model=None,faisal_ready=False)
    if args.pipeline:
        if not args.faisal_model or not args.faisal:p.error('Pipeline evaluation requires the actual Faisal model and adapter')
        from mlx_inference import MlxEngine
        router=MlxEngine(args.faisal_model,None,args.faisal)
        if not router.faisal_ready:raise RuntimeError('Actual Faisal routing required')
    args.out.mkdir(parents=True,exist_ok=False)
    engine=OllamaEngine(router,args.model,policy=args.policy)
    with urlopen('http://127.0.0.1:11434/api/tags',timeout=10) as response:tags=json.load(response)['models']
    identity=next(t for t in tags if t.get('name')==args.model or t.get('model')==args.model)
    manifest={'generator':engine.generator,'model_tag':args.model,'model_digest':identity['digest'],
        'case_sha256':hashlib.sha256(args.cases.read_bytes()).hexdigest(),
        'policy_sha256':hashlib.sha256(args.policy.read_bytes()).hexdigest() if args.policy else None,
        'mode':'actual_pipeline' if args.pipeline else 'raw_writer_without_register_substitutions',
        'seed':3407,'temperature':0,'retry_temperature':.2,'num_ctx':4096,'repeat_penalty':1.0,
        'response_adapter':'not claimed','faisal_loaded':bool(router.faisal_ready)}
    (args.out/'manifest.json').write_text(json.dumps(manifest,indent=2))
    results=[]
    try:
        for case in cases:
            start=time.monotonic()
            engine.last_generation={}
            try:
                if args.pipeline:
                    output=engine.reply(case['message'],case['relation'],case['goal'])
                else:
                    body=prompt(case['message'],case['relation'],case['goal'])[1]
                    messages=[{'role':'system','content':getattr(engine,'writer_system',SAUDI_SYSTEM)}]
                    messages+=getattr(engine,'writer_examples',[])+[body]
                    output={'reply':engine._one_generation(messages,max_tokens=256),'reply_source':engine.reply_source}
            except Exception as exc:
                output={'reply':'','status':'generation_failed','error_type':type(exc).__name__}
                if isinstance(exc,GenerationBudgetError):output['partial_text_not_sendable']=exc.partial_text
            output['last_provider_generation']=engine.last_generation
            results.append({'case':case,'output':output,'seconds':round(time.monotonic()-start,3)})
            temporary=args.out/'responses.tmp'
            temporary.write_text(json.dumps(results,ensure_ascii=False,indent=2));temporary.replace(args.out/'responses.json')
            print('Completed '+case['id'],flush=True)
    finally:
        engine._request('/api/generate',{'model':args.model,'keep_alive':0})


if __name__=='__main__':main()
