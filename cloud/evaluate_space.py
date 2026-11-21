"""Save real queued responses from an exact running LABEQ deployment.

No held-out set is selected implicitly. Public callbacks are anonymous; securely
stored Hub authentication is used only for an owned private QA Space.
"""
import argparse
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import time


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--space',required=True)
    parser.add_argument('--source',required=True,help='Expected full Git source commit')
    parser.add_argument('--cases',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--api-name',choices=['/reply','/reply_gpu'],default='/reply')
    args=parser.parse_args()
    from huggingface_hub import HfApi,get_token
    from gradio_client import Client
    import httpx
    api=HfApi();info=api.space_info(args.space);runtime=api.get_space_runtime(args.space)
    if str(runtime.stage)!='RUNNING' or runtime.raw.get('sha')!=info.sha:
        raise RuntimeError('Wait until the exact Space revision is RUNNING')
    if info.private and args.space.split('/')[0]!=api.whoami()['name']:
        raise RuntimeError('Private QA must use an owned Space')
    token=get_token() if info.private else False
    domain=runtime.raw['domains'][0]['domain'];url='https://'+domain
    headers={'Authorization':'Bearer '+token} if token else {}
    identity=None
    identity_fields=['source_commit','base_revision','adapter_revision','adapter_sha256',
        'writer_policy_sha256','repetition_penalty','generator','compute_backend','environment_versions',
        'candidate_adapter_shas','candidate_policy_sha256','v2_adapter_revision','planning_model_revision','planning_weights_sha256',
        'writer_runtime','writer_gguf_repository','writer_gguf_revision','writer_gguf_sha256','writer_gguf_adapters']
    def health():
        response=httpx.get(url+'/api/model-health',headers=headers,timeout=20)
        response.raise_for_status();data=response.json()
        if data.get('source_commit')!=args.source:
            raise RuntimeError('Live application source differs from the expected Git commit')
        if identity is not None and {key:data.get(key) for key in identity_fields}!=identity:
            raise RuntimeError('Model configuration changed during evaluation')
        return data
    observed=health()
    identity={key:observed.get(key) for key in identity_fields}
    args.out.mkdir(parents=True,exist_ok=False)
    cases=json.loads(args.cases.read_text());cases=cases['cases'] if isinstance(cases,dict) else cases
    manifest={'observed_at_utc':datetime.now(timezone.utc).isoformat(),'space':args.space,
        'space_commit':info.sha,'source_commit':args.source,'url':url,'private':info.private,
        'callback_auth':'stored private-session login' if token else 'anonymous',
        'api_name':args.api_name,'case_sha256':hashlib.sha256(args.cases.read_bytes()).hexdigest(),
        'gradio_client_version':version('gradio_client'),'health':observed}
    (args.out/'manifest.json').write_text(json.dumps(manifest,indent=2))
    client=Client(url+'/model',token=token,verbose=False,analytics_enabled=False)
    rows=[]
    for case in cases:
        if api.space_info(args.space).sha!=info.sha:
            raise RuntimeError('Space changed during evaluation; do not mix revisions')
        health();start=time.monotonic();row={'case':case}
        try:
            result=client.predict({'message':case['message'],'relation':case['relation'],
                'goal':case['goal'],'style':case.get('style','تلقائي'),
                'history':case.get('history',[]),'generation_mode':'مولّد فقط'},api_name=args.api_name)
            if not isinstance(result,dict) or not result.get('reply') or result.get('mock') is True:
                row['diagnostic_result']=result
                raise RuntimeError('Expected an actual nonempty model response')
            if result.get('reply_source') not in {'qwen_lora_generated','qwen_base_generated','ollama_generated'}:
                raise RuntimeError('Unexpected generation source')
            row['response']=result
        except Exception as exc:
            row['error']={'type':type(exc).__name__,'message':str(exc)[:500]}
        row['wall_seconds']=round(time.monotonic()-start,3);rows.append(row)
        temporary=args.out/'responses.tmp'
        temporary.write_text(json.dumps(rows,ensure_ascii=False,indent=2))
        temporary.replace(args.out/'responses.json')
        print(json.dumps({'id':case['id'],'seconds':row['wall_seconds'],
            'reply':row.get('response',{}).get('reply'),'error':row.get('error')},ensure_ascii=False),flush=True)
    if api.space_info(args.space).sha!=info.sha:raise RuntimeError('Source changed during evaluation')
    health()
    if any('error' in row for row in rows):raise SystemExit(2)


if __name__=='__main__':main()
