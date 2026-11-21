"""Package a private research diagnostic without credentials, models or paid hardware."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
LIBRARIES=['labeq_engine.py','LABEQ_V16_Coaching_Engine.py','semantic_review.py','saudi_register.py','generation_limits.py','grounded_review.py','LICENSE-CODE']


def package(destination):
    files={name:HERE/name for name in ['app.py','hybrid_pipeline.py','requirements.txt','README.md']}
    files.update({name:ROOT/name for name in LIBRARIES})
    files['writer_policy.json']=ROOT/'training/generalization/cpu_writer_policy.json'
    for name,path in files.items():
        (destination/name).write_bytes(path.read_bytes())
    selected=[str(path.relative_to(ROOT)) for path in files.values()]
    dirty=bool(subprocess.check_output(['git','status','--porcelain','--',*selected],cwd=ROOT,text=True).strip())
    manifest={'git_base_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
              'source_export':'Working-tree files; per-file SHA-256 is authoritative',
              'selected_source_has_uncommitted_changes':dirty,
              'files_sha256':{name:hashlib.sha256((destination/name).read_bytes()).hexdigest() for name in files},
              'response_adapter':None,'voice_secrets':'not included','purpose':'Private experimental CPU writer with actual Faisal routing; no quality qualification implied'}
    (destination/'source-manifest.json').write_text(json.dumps(manifest,indent=2))
    return manifest


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--space',help='Existing private free ZeroGPU Space owned by the signed-in account')
    p.add_argument('--out',type=Path,help='Create a fresh reviewable local package instead of uploading')
    args=p.parse_args()
    if bool(args.space)==bool(args.out):p.error('Choose exactly one of --space or --out')
    if args.out:
        args.out.mkdir(parents=True,exist_ok=False)
        print(json.dumps(package(args.out),indent=2));return
    from huggingface_hub import HfApi,CommitOperationAdd
    api=HfApi();info=api.space_info(args.space);runtime=api.get_space_runtime(args.space)
    if not info.private or args.space.split('/')[0]!=api.whoami()['name']:
        raise RuntimeError('This publisher requires an owned private diagnostic Space')
    hardware=[str(value) for value in [runtime.hardware,runtime.requested_hardware] if value is not None]
    if not hardware or any(value!='zero-a10g' for value in hardware):
        raise RuntimeError('Requires existing free ZeroGPU; never requests paid hardware')
    with tempfile.TemporaryDirectory(prefix='labeq-cpu-diagnostic-') as temp:
        directory=Path(temp);package(directory)
        result=api.create_commit(args.space,repo_type='space',operations=[CommitOperationAdd(path_in_repo=file.name,path_or_fileobj=file) for file in directory.iterdir()],commit_message='Update private LABEQ CPU diagnostic from explicit source allowlist')
    print(json.dumps({'space':args.space,'commit':result.oid}))


if __name__=='__main__':main()
