"""Read a writing prompt policy without executing code or loading model weights."""
import json
from pathlib import Path


def read_policy(path):
    settings=json.loads(Path(path).read_text(encoding="utf-8"))
    system,examples=settings.get("system"),settings.get("examples",[])
    if not isinstance(system,str) or not system.strip() or not isinstance(examples,list):
        raise ValueError("Writing policy must have a system string and an examples list")
    if len(examples)>10 or len(examples)%2:
        raise ValueError("Writing examples must be at most five complete pairs")
    for i,example in enumerate(examples):
        if not isinstance(example,dict) or example.get("role")!=("user" if i%2==0 else "assistant"):
            raise ValueError("Writing examples must alternate user and assistant")
        if not isinstance(example.get("content"),str) or not example["content"].strip():
            raise ValueError("Writing examples must contain text")
    return system,[{"role":e["role"],"content":e["content"]} for e in examples]
