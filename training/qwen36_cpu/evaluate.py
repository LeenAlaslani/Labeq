"""Record an explicitly selected CPU diagnostic; never choose a holdout implicitly."""
import argparse,hashlib,json,subprocess,time
from datetime import datetime,timezone
from pathlib import Path


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--space',required=True);p.add_argument('--source',required=True)
    p.add_argument('--cases',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--policy',choices=['clean','fewshot'],required=True)
    p.add_argument('--mode',choices=['raw','pipeline'],default='raw');args=p.parse_args()
    from huggingface_hub import HfApi,get_token
    from gradio_client import Client
    api=HfApi();info=api.space_info(args.space)
    if not info.private or args.space.split('/')[0]!=api.whoami()['name']:raise RuntimeError('Owned private diagnostic only')
    runtime=api.get_space_runtime(args.space)
    if str(runtime.stage)!='RUNNING' or runtime.raw.get('sha')!=info.sha:raise RuntimeError('Exact Space revision not running')
    client=Client(args.space,token=get_token(),verbose=False,analytics_enabled=False)
    meta=client.predict(api_name='/metadata')
    if meta.get('source_commit')!=args.source:raise RuntimeError('Live diagnostic source differs')
    policy_bytes=subprocess.check_output(['git','show',f'{args.source}:training/qwen36_cpu/writer_{args.policy}.json'])
    policy=json.loads(policy_bytes)
    cases=json.loads(args.cases.read_text());cases=cases['cases'] if isinstance(cases,dict) else cases
    args.out.mkdir(exist_ok=False,parents=True)
    manifest={'at_utc':datetime.now(timezone.utc).isoformat(),'source_commit':args.source,'space_revision':info.sha,
        'case_sha256':hashlib.sha256(args.cases.read_bytes()).hexdigest(),'policy':args.policy,
        'policy_sha256':hashlib.sha256(policy_bytes).hexdigest(),'mode':args.mode,'metadata_before_loading':meta}
    (args.out/'manifest.json').write_text(json.dumps(manifest,indent=2))
    results=[]
    for case in cases:
        if api.space_info(args.space).sha!=info.sha:raise RuntimeError('Deployment changed during evaluation')
        start=time.monotonic();row={'case':case}
        try:
            if args.mode=='pipeline':
                result=client.predict({'cases':[case],'policy':args.policy},api_name='/pipeline')
            else:
                text=f"الموقف: {case['message']}\nالعلاقة: {case['relation']}\nالهدف: {case['goal']}\nالأسلوب: عفوي\nاكتب الرسالة للطرف الآخر، واحفظ كل الطلبات والقيود بدون اختصار يضيع المعنى."
                messages=[{'role':'system','content':policy['system']}]+policy['examples']+[{'role':'user','content':text}]
                result=client.predict({'rows':[{'id':case['id'],'messages':messages}]},api_name='/check')
            if result.get('metadata',{}).get('source_commit')!=args.source:raise RuntimeError('Response source differs')
            row['result']=result
        except Exception as exc:row['error']={'type':type(exc).__name__,'message':str(exc)[:700]}
        row['request_seconds']=round(time.monotonic()-start,3);results.append(row)
        temporary=args.out/'responses.tmp';temporary.write_text(json.dumps(results,ensure_ascii=False,indent=2));temporary.replace(args.out/'responses.json')
        print(json.dumps(row,ensure_ascii=False),flush=True)
    if api.space_info(args.space).sha!=info.sha:raise RuntimeError('Deployment changed during evaluation')
    if any('error' in row for row in results):raise SystemExit(2)


if __name__=='__main__':main()
