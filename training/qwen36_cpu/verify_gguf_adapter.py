"""Verify every F32 GGUF LoRA factor against its preserved PEFT source.

Run with PYTHONPATH pointing to the official pinned llama.cpp gguf-py folder.
This intentionally supports only LABEQ's existing seven target suffixes; it
rejects an unrecognised transformation instead of silently dropping weights.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

import numpy as np
from safetensors.numpy import load_file

CONVERTER_REVISION='0c1e57098bba43ac29e6e3b677cdceebdd22334f'
SUFFIXES={'mlp.down_proj':'ffn_down','mlp.up_proj':'ffn_up','mlp.gate_proj':'ffn_gate',
          'self_attn.q_proj':'attn_q','self_attn.k_proj':'attn_k',
          'self_attn.v_proj':'attn_v','self_attn.o_proj':'attn_output'}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify(source,destination):
    from gguf import GGUFReader
    source=Path(source);destination=Path(destination)
    config=json.loads((source/'adapter_config.json').read_text())
    if config['r']!=16 or config['lora_alpha']!=16 or config.get('use_dora') or config.get('use_rslora'):
        raise ValueError('Unsupported scaling')
    reader=GGUFReader(destination)
    factors={t.name:t for t in reader.tensors}
    expected={}
    for name,value in load_file(source/'adapter_model.safetensors').items():
        match=re.fullmatch(r'base_model\.model\.model\.language_model\.layers\.(\d+)\.(.+)\.lora_([AB])\.weight',name)
        if match is None or match[2] not in SUFFIXES:raise ValueError('Unrecognised tensor '+name)
        target=f'blk.{match[1]}.{SUFFIXES[match[2]]}.weight.lora_{match[3].lower()}'
        tensor=factors[target]
        if tensor.tensor_type!=0 or tensor.data.shape!=value.shape or not np.array_equal(tensor.data,value):
            raise ValueError('Factor differs: '+name)
        expected[target]=value
    if set(expected)!=set(factors):raise ValueError('Missing or extra tensors')
    alpha=reader.fields['adapter.lora.alpha']
    if float(alpha.parts[alpha.data[0]][0])!=config['lora_alpha']:raise ValueError('GGUF scaling differs')
    return {'peft_sha256':sha(source/'adapter_model.safetensors'),'gguf_sha256':sha(destination),
            'gguf_file':destination.name,'tensor_count':len(expected),'all_factors_exact':True,
            'format':'F32 GGUF LoRA, alpha/r=1; no merged or quantized adapter factors',
            'converter_repository':'ggml-org/llama.cpp','converter_revision':CONVERTER_REVISION}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path);parser.add_argument('destination',type=Path)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();result=verify(args.source,args.destination)
    args.out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
