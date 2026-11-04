"""Convert the exact uploaded PEFT adapter to mlx-vlm explicit-key LoRA.
Raises on unexpected keys; no training or loss of checkpoint precision.
"""
import argparse
import json
import re
from pathlib import Path
from zipfile import ZipFile
import numpy as np
from safetensors.numpy import load as st_load, save_file

PAT = re.compile(
    r'^base_model\.model\.model\.language_model\.'
    r'(layers\.\d+\.(?:mlp\.(?:down_proj|gate_proj|up_proj)|self_attn\.(?:q_proj|k_proj|v_proj|o_proj)))'
    r'\.lora_([AB])\.weight$'
)
SOURCE_CONFIG = 'Labeq_Qwen35_4B_Pilot_LoRA/adapter_config.json'
SOURCE_WEIGHTS = 'Labeq_Qwen35_4B_Pilot_LoRA/adapter_model.safetensors'

def convert(zip_path: Path, output_dir: Path):
    if not zip_path.is_file():
        raise FileNotFoundError(f'لا يوجد الملف: {zip_path}')
    with ZipFile(zip_path) as z:
        names=set(z.namelist())
        if SOURCE_CONFIG not in names or SOURCE_WEIGHTS not in names:
            raise ValueError('الملف ليس نسخة أوزان لبق المتوقعة')
        source_config=json.loads(z.read(SOURCE_CONFIG))
        weights=st_load(z.read(SOURCE_WEIGHTS))
    if source_config.get('peft_type')!='LORA':
        raise ValueError('نوع الأوزان غير متوقع')
    if source_config.get('base_model_name_or_path')!='unsloth/Qwen3.5-4B':
        raise ValueError('اسم المودل الأساسي مختلف؛ لا تستخدمي هذا المحول')
    rank=source_config['r']; alpha=source_config['lora_alpha']
    if rank != 16 or alpha != 16:
        raise ValueError('إعدادات LoRA غير مطابقة للإصدار الذي تم فحصه')
    converted={}; pairs={}
    for old_key, value in weights.items():
        m=PAT.fullmatch(old_key)
        if not m: raise ValueError(f'مفتاح غير متوقع، توقّف التحويل: {old_key}')
        suffix, letter=m.groups()
        full_name='language_model.model.'+suffix
        new_key=full_name+'.lora_'+letter.lower()
        if new_key in converted: raise ValueError('تكرار: '+new_key)
        if value.ndim!=2 or value.shape[0 if letter=='A' else 1]!=rank:
            raise ValueError('أبعاد غير متوافقة: '+old_key)
        converted[new_key]=np.ascontiguousarray(value.T)
        pairs.setdefault(full_name,set()).add(letter)
    if len(weights)!=256 or len(pairs)!=128 or any(v!={'A','B'} for v in pairs.values()):
        raise ValueError('الأوزان غير مكتملة')
    target=output_dir
    target.mkdir(parents=True,exist_ok=True)
    config={
        'fine_tune_type':'lora',
        'num_layers':-1,
        'lora_parameters':{
            'rank':rank,'scale':alpha/rank,'dropout':0.0,
            'keys':sorted(pairs)
        }
    }
    # mlX LoRALinear: A(in,rank), B(rank,out); PEFT uses A(rank,in), B(out,rank).
    save_file(converted,str(target/'adapters.safetensors'))
    (target/'adapter_config.json').write_text(json.dumps(config,ensure_ascii=False,indent=2))
    # Independent roundtrip shape/content test, not inference validation.
    from safetensors import safe_open
    with safe_open(str(target/'adapters.safetensors'),framework='numpy') as out:
        if len(out.keys())!=len(converted): raise ValueError('فشل حفظ جميع الأوزان')
        for k in converted:
            if not np.array_equal(out.get_tensor(k),converted[k]):
                raise ValueError('فشل اختبار النقل: '+k)
    print('✅ تم تحويل 256 مصفوفة LoRA (128 طبقة/وحدة) بدون حذف أي أوزان.')
    print('✅ تحققنا من الملفات الناتجة. باقي اختبار تحميل الأوزان وتوليدها على جهاز M5.')
    return target

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--zip',type=Path,required=True)
    parser.add_argument('--output',type=Path,default=Path(__file__).resolve().parent/'mlx_adapter')
    args=parser.parse_args()
    convert(args.zip.expanduser(),args.output.expanduser())
