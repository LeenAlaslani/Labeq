"""Record actual private CPU diagnostic outputs without opening a held-out set implicitly."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import time

ROOT=Path(__file__).resolve().parents[3]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--space',required=True)
    p.add_argument('--cases',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--mode',choices=['raw','pipeline'],default='pipeline')
    p.add_argument('--temperature',type=float,choices=[0,.7],default=0)
    args=p.parse_args()
    from huggingface_hub import HfApi,get_token
    from gradio_client import Client
    api=HfApi();info=api.space_info(args.space)
    if not info.private:raise RuntimeError('Do not forward private-session credentials to an unnecessary public diagnostic')
    token=get_token()
    if not token:raise RuntimeError('Connect securely with hf auth login in Terminal')
    args.out.mkdir(parents=True,exist_ok=False)
    client=Client(args.space,token=token,verbose=False,analytics_enabled=False)
    policy_path=ROOT/'training/generalization/cpu_writer_policy.json'
    policy=json.loads(policy_path.read_text())
    cases=json.loads(args.cases.read_text());cases=cases['cases'] if isinstance(cases,dict) else cases
    manifest={'at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'space':args.space,'space_source_revision':info.sha,
              'case_sha256':hashlib.sha256(args.cases.read_bytes()).hexdigest(),'policy_sha256':hashlib.sha256(policy_path.read_bytes()).hexdigest(),
              'mode':args.mode,'raw_temperature':args.temperature,'metadata':client.predict(api_name='/metadata')}
    (args.out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
    rows=[]
    for case in cases:
        if api.space_info(args.space).sha!=info.sha:raise RuntimeError('Diagnostic source changed during evaluation; do not mix revisions')
        start=time.monotonic()
        try:
            if args.mode=='pipeline':
                result=client.predict({'cases':[case]},api_name='/pipeline')
            else:
                body=f"الموقف: {case['message']}\nالعلاقة: {case['relation']}\nالهدف: {case['goal']}\nالأسلوب: عفوي\nاكتب الرسالة للطرف الآخر، واحفظ كل الطلبات والقيود بدون اختصار يضيع المعنى."
                messages=[{'role':'system','content':policy['system']}]+policy['examples']+[{'role':'user','content':body}]
                result=client.predict({'rows':[{'id':case['id'],'messages':messages}],'temperature':args.temperature},api_name='/check')
            row={'case':case,'result':result,'request_seconds':time.monotonic()-start}
        except Exception as exc:
            row={'case':case,'error_type':type(exc).__name__,'error':str(exc)[:1000],'request_seconds':time.monotonic()-start}
        rows.append(row)
        temp=args.out/'responses.tmp';temp.write_text(json.dumps(rows,ensure_ascii=False,indent=2));temp.replace(args.out/'responses.json')
        print('Recorded '+case['id'],flush=True)


if __name__=='__main__':main()
