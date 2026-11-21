"""Publish only exact committed diagnostic source to an owned private free Space."""
import argparse,hashlib,json,subprocess,tempfile
from pathlib import Path


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--space',required=True);p.add_argument('--commit',default='HEAD');args=p.parse_args()
    from huggingface_hub import HfApi,CommitOperationAdd
    api=HfApi();info=api.space_info(args.space);r=api.get_space_runtime(args.space)
    if not info.private or args.space.split('/')[0]!=api.whoami()['name']:raise RuntimeError('Owned private Space required')
    hardware=[str(x) for x in [r.hardware,r.requested_hardware] if x is not None]
    if not hardware or any(x!='zero-a10g' for x in hardware):raise RuntimeError('Existing free hardware only')
    source=subprocess.check_output(['git','rev-parse',args.commit],text=True).strip()
    names={name:'training/qwen36_cpu/'+name for name in ['app.py','hybrid_pipeline.py','requirements.txt','writer_clean.json','writer_fewshot.json','protocol.json','greedy_protocol.json']}
    names['README.md']='training/qwen36_cpu/SPACE_README.md'
    for name in ['labeq_engine.py','LABEQ_V16_Coaching_Engine.py','semantic_review.py','saudi_register.py','generation_limits.py','grounded_review.py','LICENSE-CODE']:names[name]=name
    with tempfile.TemporaryDirectory(prefix='labeq-qwen36-') as directory:
        folder=Path(directory)
        for target,path in names.items():
            (folder/target).write_bytes(subprocess.check_output(['git','show',f'{source}:{path}']))
        manifest={'source_commit':source,'files_sha256':{name:hashlib.sha256((folder/name).read_bytes()).hexdigest() for name in names},'response_adapter':None,'provider_secrets':'excluded'}
        (folder/'source-manifest.json').write_text(json.dumps(manifest,indent=2))
        result=api.create_commit(args.space,repo_type='space',operations=[CommitOperationAdd(path_in_repo=f.name,path_or_fileobj=f) for f in folder.iterdir()],commit_message='Private Qwen3.6 CPU diagnostic source '+source[:12])
    print(json.dumps({'space':args.space,'source_commit':source,'space_commit':result.oid}))


if __name__=='__main__':main()
