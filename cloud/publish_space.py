"""Publish an exact Git source commit to an existing free ZeroGPU Space."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

from huggingface_hub import CommitOperationAdd, HfApi
from huggingface_hub.utils import disable_progress_bars


def main():
    disable_progress_bars()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--space", required=True)
    parser.add_argument("--commit", default="HEAD")
    parser.add_argument("--backend", choices=["gpu", "cpu", "ensemble"], default="gpu")
    parser.add_argument("--private-adapter", type=Path, help="Copy QA weights only into an owned PRIVATE Space")
    parser.add_argument("--private-v2",type=Path,help="Second QA adapter; owned private ensemble Space only")
    args = parser.parse_args()
    source = subprocess.check_output(["git", "rev-parse", args.commit], text=True).strip()
    api = HfApi()
    runtime = api.get_space_runtime(args.space)
    hardware = [value for value in (runtime.hardware, runtime.requested_hardware) if value]
    if not hardware or any(value != "zero-a10g" for value in hardware):
        raise RuntimeError(f"Expected existing free ZeroGPU hardware, found {hardware}")
    if args.private_adapter:
        info = api.space_info(args.space)
        if args.backend not in {"cpu","ensemble"} or not info.private or args.space.split('/')[0] != api.whoami()['name']:
            raise RuntimeError("QA adapter uploads require CPU mode and an owned private Space")
    if args.private_v2 and (not args.private_adapter or args.backend!='ensemble'):
        raise RuntimeError('Second QA weights require a private ensemble adapter upload')
    names = subprocess.check_output(["git", "ls-tree", "-r", "--name-only", source], text=True).splitlines()
    selected = [
        name for name in names
        if name.startswith("assets/")
        or ("/" not in name and Path(name).suffix in {".py", ".js", ".html", ".css"})
        or name in {"cloud/space_app.py", "cloud/torch_engine.py", "cloud/cpu_engine.py", "cloud/cpu_space_app.py", "cloud/ensemble_engine.py", "cloud/ensemble_space_app.py", "cloud/semantic_teacher.py", "training/generalization_v3/policy.json", "training/qwen36_cpu/writer_fewshot.json", "LICENSE-CODE"}
    ]

    def content(name):
        return subprocess.check_output(["git", "show", f"{source}:{name}"])

    with tempfile.TemporaryDirectory(prefix="labeq-space-") as temporary:
        directory = Path(temporary)
        for name in selected:
            destination = directory / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(content(name))
        readme = content("cloud/ENSEMBLE_README.md" if args.backend=='ensemble' else "cloud/SPACE_README.md").decode()
        if args.backend == "cpu":
            readme = readme.replace('app_file: cloud/space_app.py', 'app_file: cloud/cpu_space_app.py')
            readme += "\nBackend: actual CPU Qwen/Faisal at /reply; optional real ZeroGPU inference at /reply_gpu. CPU transport does not establish reply quality.\n"
        readme += f"\nSource commit {source}.\n"
        (directory / "README.md").write_text(readme)
        runtime_requirements='cloud/requirements-cpu.txt' if args.backend in {'cpu','ensemble'} else 'cloud/requirements-zerogpu.txt'
        requirements=content("requirements.txt") + b"\n" + content(runtime_requirements)
        if args.backend=='ensemble':requirements+=b'\n'+content('cloud/requirements-ensemble.txt')
        (directory / "requirements.txt").write_bytes(requirements)
        adapter_manifest = None
        if args.private_adapter:
            for filename in ('adapter_config.json', 'adapter_model.safetensors'):
                target = directory / 'private-qa-adapter' / filename
                target.parent.mkdir(exist_ok=True)
                target.write_bytes((args.private_adapter / filename).read_bytes())
            adapter_manifest = {'purpose': 'Private QA only', 'files_sha256': {
                file.name: hashlib.sha256(file.read_bytes()).hexdigest()
                for file in (directory / 'private-qa-adapter').iterdir()}}
        if args.private_v2:
            for filename in ('adapter_config.json','adapter_model.safetensors'):
                target=directory/'private-qa-v2'/filename;target.parent.mkdir(exist_ok=True)
                target.write_bytes((args.private_v2/filename).read_bytes())
            adapter_manifest['second_adapter_sha256']={file.name:hashlib.sha256(file.read_bytes()).hexdigest()
                for file in (directory/'private-qa-v2').iterdir()}
        manifest = {
            "source_commit": source,
            "backend": args.backend,
            "private_qa_adapter": adapter_manifest,
            "files_sha256": {
                str(file.relative_to(directory)): hashlib.sha256(file.read_bytes()).hexdigest()
                for file in sorted(directory.rglob("*")) if file.is_file()
            },
        }
        (directory / "source-manifest.json").write_text(json.dumps(manifest, indent=2))
        operations = [
            CommitOperationAdd(path_in_repo=str(file.relative_to(directory)), path_or_fileobj=file)
            for file in sorted(directory.rglob("*")) if file.is_file()
        ]
        commit = api.create_commit(
            repo_id=args.space, repo_type="space", operations=operations,
            commit_message=f"Deploy LABEQ source {source[:12]} on ZeroGPU",
        )
        print(json.dumps({"space": args.space, "source_commit": source,
                          "space_commit": commit.oid}, indent=2))


if __name__ == "__main__":
    main()
