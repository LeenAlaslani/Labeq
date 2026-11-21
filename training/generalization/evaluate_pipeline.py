"""Run actual Faisal routing, writer and grounded reviewer; save complete traces."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from mlx_inference import MlxEngine


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--model",required=True)
    p.add_argument("--adapter",type=Path,required=True)
    p.add_argument("--label",required=True)
    p.add_argument("--faisal",type=Path,required=True)
    p.add_argument("--cases",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    cases=json.loads(args.cases.read_text())
    if isinstance(cases,dict):cases=cases["cases"]
    args.out.mkdir(parents=True,exist_ok=False)
    engine=MlxEngine(args.model,args.adapter,args.faisal,args.label)
    if not engine.faisal_ready:raise RuntimeError("Real Faisal adapter required")
    results=[]
    for i,case in enumerate(cases):
        engine.mx.random.seed(3407+i)
        start=time.monotonic()
        output=engine.reply(case["message"],case["relation"],case["goal"])
        results.append({"case":case,"output":output,"seconds":round(time.monotonic()-start,3)})
        (args.out/"responses.json").write_text(json.dumps(results,ensure_ascii=False,indent=2))
        print(json.dumps({"id":case["id"],"reply":output["reply"],"review":output["review_status"],"retried":output["was_retried"],"seconds":results[-1]["seconds"]},ensure_ascii=False),flush=True)
    (args.out/"manifest.json").write_text(json.dumps({"case_sha256":hashlib.sha256(args.cases.read_bytes()).hexdigest(),"generator":engine.generator,"seed":3407,"faisal_loaded":engine.faisal_ready},indent=2))


if __name__=="__main__":main()
