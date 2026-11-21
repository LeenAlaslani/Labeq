"""Experimental adapter, separate from the completed approved Saudi LoRA v2."""
import argparse
from dataclasses import asdict
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import random
import time

from train_mlx import prepare
from validate_data import read_rows

TARGETS = ["q_proj","k_proj","v_proj","o_proj","gate_proj","up_proj","down_proj", "in_proj_qkv", "out_proj"]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--data",type=Path,required=True)
    p.add_argument("--model",required=True)
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    import mlx.core as mx
    import mlx.optimizers as optim
    import numpy as np
    from mlx_vlm import load
    from mlx_vlm.trainer.api import Trainer, task_spec
    from mlx_vlm.trainer.common.model import prepare_model_for_training
    random.seed(3407); np.random.seed(3407); mx.random.seed(3407)
    rows=read_rows(args.data/"train.jsonl")
    manifest=json.loads((args.data/"manifest.json").read_text())
    if len(rows)!=manifest["training_rows"]:
        raise ValueError("Training manifest mismatch")
    if hashlib.sha256((args.data/"train.jsonl").read_bytes()).hexdigest()!=manifest["sha256"][str(args.data/"train.jsonl")]:
        raise ValueError("Training hash mismatch")
    args.out.mkdir(parents=True,exist_ok=False)
    model,processor=load(args.model)
    train=prepare(rows,processor.tokenizer,mx)
    val=prepare(read_rows(args.data/"validation.jsonl"),processor.tokenizer,mx)
    model=prepare_model_for_training(model,lora_rank=16,lora_alpha=16,target_modules=TARGETS)
    _,(_,config_class)=task_spec("vlm","sft")
    epoch_steps=len(train)//2
    cfg=config_class(batch_size=2,iters=epoch_steps*2,gradient_accumulation_steps=2,
        max_seq_length=768,val_batches=len(val)//2,steps_per_eval=epoch_steps,
        steps_per_save=epoch_steps,steps_per_report=10,adapter_file=str(args.out/"adapters.safetensors"),
        train_on_completions=True,grad_checkpoint=True)
    updates=cfg.iters//2; warmup=max(1,round(updates*.05))
    lr=optim.join_schedules([optim.linear_schedule(1e-7,1e-4,warmup),optim.cosine_decay(1e-4,updates-warmup)],[warmup])
    trainer=Trainer(model,cfg,optimizer=optim.AdamW(lr,weight_decay=0),train_dataset=train,eval_dataset=val,
        processing_class=processor,prepared=True,seed=3407)
    details={"status":"experimental_not_approved_v2","config":asdict(cfg),"targets":TARGETS,"seed":3407,
        "rank":16,"alpha":16,"lr":1e-4,"epochs":2,"base":args.model,"mlx":version("mlx"),
        "mlx_vlm":version("mlx-vlm"),"device":str(mx.default_device()),"data_manifest":manifest}
    (args.out/"run_config.json").write_text(json.dumps(details,ensure_ascii=False,indent=2))
    print(json.dumps({"steps":cfg.iters,"train_rows":len(train),"target_suffixes":TARGETS}),flush=True)
    start=time.monotonic()
    metrics=trainer.train()
    result={"metrics":metrics,"validation":trainer.evaluate(),"history":trainer.log_history,"elapsed_seconds":time.monotonic()-start}
    (args.out/"metrics.json").write_text(json.dumps(result,indent=2,default=str))
    print(json.dumps({"validation":result["validation"],"elapsed_seconds":result["elapsed_seconds"]}),flush=True)


if __name__=="__main__":main()
