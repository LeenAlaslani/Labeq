"""Generate raw paired outputs on frozen cases, without dialect substitutions."""
import argparse
import hashlib
import json
from pathlib import Path
import random
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from mlx_inference import MlxEngine
from training.generalization.build import prompt
from writing_policy import read_policy


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--model",required=True)
    p.add_argument("--pilot",type=Path,required=True)
    p.add_argument("--v2",type=Path)
    p.add_argument("--candidate",type=Path,action="append",default=[])
    p.add_argument("--cases",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--policy",type=Path)
    p.add_argument("--plans",type=Path,help="Unedited automatic planning.py responses; never reference answers")
    args=p.parse_args()
    policy=read_policy(args.policy) if args.policy else None
    cases=json.loads(args.cases.read_text())
    if isinstance(cases,dict):cases=cases["cases"]
    plans={}
    if args.plans:
        from training.qwen36_cpu.planning import parse_plan
        for row in json.loads(args.plans.read_text()):
            source=row['planning_result'];choice=source['rows'][0]
            if choice['finish_reason']!='stop':raise ValueError('Incomplete automatic plan')
            plans[row['case']['id']]={'case':row['case'],'plan':parse_plan(choice['reply']),
                'runtime_source':source['metadata']['source_commit']}
        if set(plans)!={case['id'] for case in cases}:raise ValueError('Plan/case IDs differ')
        if any(plans[case['id']]['case']!=case for case in cases):raise ValueError('Automatic plan belongs to a different original case')
    args.out.mkdir(parents=True,exist_ok=False)
    engine=MlxEngine(args.model,args.pilot)
    adapters={"base":"base","pilot":"saudi"}
    if args.v2:
        engine.adapters["v2"]=engine._adapter_layers(args.v2);adapters["v2"]="v2"
    for i,path in enumerate(args.candidate):
        key=f"candidate_{i+1}"
        engine.adapters[key]=engine._adapter_layers(path);adapters[key]=key
    manifest={"cases_sha256":hashlib.sha256(args.cases.read_bytes()).hexdigest(),
        "base":args.model,"adapters":{},"policy_sha256":hashlib.sha256(args.policy.read_bytes()).hexdigest() if args.policy else None,
        "automatic_plans_sha256":hashlib.sha256(args.plans.read_bytes()).hexdigest() if args.plans else None,
        "plan_runtime_sources":sorted({row['runtime_source'] for row in plans.values()}),"manual_oracle":False,
        "generation":{"max_tokens":256,"temperature":0,"thinking":False,"surface_normalization":False}}
    for name,path in [("pilot",args.pilot),("v2",args.v2)]+[(f"candidate_{i+1}",p) for i,p in enumerate(args.candidate)]:
        if path:
            weights=path/("adapter_model.safetensors" if (path/"adapter_model.safetensors").exists() else "adapters.safetensors")
            manifest["adapters"][name]={"directory":str(path),"sha256":hashlib.sha256(weights.read_bytes()).hexdigest()}
    (args.out/"manifest.json").write_text(json.dumps(manifest,indent=2))
    results=[];blind=[];keys=[];rng=random.Random(7319)
    for case in cases:
        outputs={}
        for name,adapter in adapters.items():
            start=time.monotonic()
            messages=prompt(case["message"],case["relation"],case["goal"])
            if policy:messages=[{"role":"system","content":policy[0]}]+policy[1]+messages[1:]
            if plans:
                messages[-1]['content']+='\nتحليل آلي استرشادي للطلبات، وليس مصدرا للحقائق. النص الأصلي هو المرجع إذا تعارض معه:\n'+json.dumps(plans[case['id']]['plan'],ensure_ascii=False)
            reply=engine.generate(messages,adapter,max_tokens=256,temperature=0)
            outputs[name]={"reply":reply,"seconds":round(time.monotonic()-start,3),"generation":engine.last_generation}
        results.append({"case":case,"outputs":outputs})
        order=list(outputs);rng.shuffle(order)
        for i,name in enumerate(order):
            anonymous=f"{case['id']}-{i+1}"
            blind.append({"candidate":anonymous,"case":case,"reply":outputs[name]["generation"]["decoded_text"]})
            keys.append({"candidate":anonymous,"model":name})
        (args.out/"responses.json").write_text(json.dumps(results,ensure_ascii=False,indent=2))
        print(f"Completed {case['id']}",flush=True)
    (args.out/"blind.json").write_text(json.dumps(blind,ensure_ascii=False,indent=2))
    (args.out/"blind_key.json").write_text(json.dumps(keys,indent=2))


if __name__=="__main__":main()
