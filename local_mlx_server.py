"""Local-only Qwen3.5-4B + trained Saudi LoRA backend for LABEQ V12.
This does NOT contain a trained Faisal classifier. Router is clearly identified as rules.
"""
from __future__ import annotations
import os,re,threading
from pathlib import Path
from functools import lru_cache
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel,Field
from dotenv import load_dotenv
import secrets

ROOT=Path(__file__).resolve().parent
load_dotenv(ROOT/'.env')
SECRET=(ROOT/'.local_api_key').read_text().strip() if (ROOT/'.local_api_key').exists() else ''
if len(SECRET)<16: raise RuntimeError('شغّلي bash prepare_local.sh أولًا لإنشاء إعدادات الأمان.')
MODEL='mlx-community/Qwen3.5-4B-MLX-4bit'
ADAPTER=ROOT/'mlx_adapter'
if not (ADAPTER/'adapters.safetensors').exists():
    raise RuntimeError('لم يتم تحويل أوزان LoRA بعد. شغّلي bash prepare_local.sh')

app=FastAPI(title='LABEQ Mac Backup — Saudi LoRA',docs_url=None,redoc_url=None)
engine_lock=threading.Lock()
model_loaded=False
faisal_loaded=False

class Turn(BaseModel):
    role:str=Field(pattern='^(user|assistant)$')
    content:str=Field(max_length=500)

class ReplyRequest(BaseModel):
    message:str=Field(min_length=1,max_length=2000)
    relation:str=Field(default='شخص آخر',max_length=100)
    goal:str=Field(default='أبي رد مناسب',max_length=300)
    style:str='تلقائي'
    speaker_gender:str='غير محدد'
    recipient_gender:str='غير محدد'
    history:list[Turn]=Field(default_factory=list,max_length=6)
    generation_mode:str='مولّد فقط'

STYLES={'polite':'لطيف','firm':'حازم','diplomatic':'دبلوماسي','apology':'اعتذار','clarify':'طلب توضيح'}
SYSTEM_PROMPT="""أنت «لبق»، تصيغين رسالة سعودية قصيرة جاهزة لإرسالها للطرف الآخر، بدون شرح.
استخدمي صياغة سعودية طبيعية في الأصدقاء والعائلة، ومهنية بسيطة في العمل والعملاء.
اكتبي جملة أو جملتين فقط، دون مقدمات مثل «إليك الرد»، ولا تختلقي تفاصيل.
عند الطلب من أنثى، لا تستخدمي صيغة المتكلم المذكر. احترمي العلاقة والهدف والأسلوب.
اكتبي الرد مباشرة فقط. ممنوع تكرار التعليمات أو إظهار خطوات تفكير."""

def fallback_style(goal:str,message:str)->str:
    g=(goal or '').lower()
    if 'حدود' in g or 'حزم' in g or 'مسؤولياتي' in g:return 'firm'
    if 'أرفض' in g or 'ارفض' in g:return 'polite'
    if 'خلاف' in g or 'صلح' in g or 'تفاهم' in g or 'سوء' in g:return 'diplomatic'
    if 'أعتذر' in g or 'اعتذر' in g or 'أعتذار' in g:return 'apology'
    if 'توضيح' in g or 'أفهم' in g or 'افهم' in g or 'المقصود' in g:return 'clarify'
    return 'clarify'

@lru_cache(maxsize=1)
def load_engine():
    global model_loaded
    from mlx_vlm import load
    from mlx.utils import tree_flatten
    import mlx.core as mx
    print('تحميل Qwen3.5-4B المضغوط مع Saudi LoRA...',flush=True)
    model,processor=load(MODEL, adapter_path=str(ADAPTER))
    # Fail closed if any LoRA tensor did not attach; never silently return base output.
    adapter_weights=mx.load(str(ADAPTER/'adapters.safetensors'))
    params=dict(tree_flatten(model.parameters()))
    missing=[k for k in adapter_weights if k not in params]
    if missing:
        raise RuntimeError(f'لم يتم تركيب {len(missing)} من أوزان LoRA على المودل. مثال: {missing[0]}')
    bad=[k for k,v in adapter_weights.items() if tuple(params[k].shape)!=tuple(v.shape)]
    if bad:raise RuntimeError('أبعاد LoRA غير متوافقة مع النموذج: '+bad[0])
    if len(adapter_weights)!=256:raise RuntimeError('عدد أوزان LoRA غير متوقع')
    for key in list(sorted(adapter_weights))[:2]+list(sorted(adapter_weights))[-2:]:
        try:
            diff=float(mx.max(mx.abs(params[key].astype(mx.float32)-adapter_weights[key].astype(mx.float32))).item())
        except Exception as e:
            raise RuntimeError('تعذر التحقق من تركيب LoRA: '+key) from e
        if diff>0.01: raise RuntimeError(f'قيم LoRA المحمّلة لا تطابق الملف: {key} | diff={diff}')
    model_loaded=True
    print('✅ تم تحميل Qwen مع كل مصفوفات LoRA الـ256 والتحقق من أبعادها وقيم عينة منها.',flush=True)
    return model,processor

@app.on_event('startup')
async def start():
    load_engine()

@app.get('/health')
def health():
    return {'service':'labeq-mac','status':'online','model_loaded':model_loaded,
            'faisal_loaded':False,'router':'rule_fallback',
            'backend':'mlx-vlm','adapter_loaded':model_loaded}

def extract_text(g):
    raw=g.text if hasattr(g,'text') else (g.get('text','') if isinstance(g,dict) else str(g))
    raw=re.sub(r'<think>.*?</think>','',raw,flags=re.S)
    return raw.replace('<|im_end|>','').strip().strip('"“”')

@app.post('/v1/reply')
async def reply(req:ReplyRequest,x_api_key:str|None=Header(default=None)):
    if not secrets.compare_digest(x_api_key or '',SECRET):raise HTTPException(401,'Unauthorized')
    if req.generation_mode!='مولّد فقط':raise HTTPException(422,'Only generated text is supported')
    if not model_loaded:raise HTTPException(503,'Model not loaded')
    selected={'لطيف':'polite','حازم':'firm','دبلوماسي':'diplomatic','اعتذار':'apology','طلب توضيح':'clarify'}.get(req.style)
    style_key=selected or fallback_style(req.goal,req.message)
    label=req.style if req.style not in ('تلقائي','',None) else STYLES[style_key]
    lines=[{'role':'system','content':SYSTEM_PROMPT}]
    lines.extend({'role':t.role,'content':t.content} for t in req.history[-4:])
    lines.append({'role':'user','content':f'الموقف: {req.message}\nالعلاقة: {req.relation}\nالهدف: {req.goal}\nالأسلوب: {label}\nجنس المتحدث: {req.speaker_gender}\nجنس المخاطب: {req.recipient_gender}\nاكتبي الرد الجاهز فقط بلهجة سعودية مناسبة.'})
    model,proc=load_engine()
    tokenizer=proc.tokenizer if hasattr(proc,'tokenizer') else proc
    try: prompt=tokenizer.apply_chat_template(lines,tokenize=False,add_generation_prompt=True,enable_thinking=False)
    except TypeError: prompt=tokenizer.apply_chat_template(lines,tokenize=False,add_generation_prompt=True)
    try:
        from mlx_vlm import generate
        # Some versions accept prompt strings; keep one model loaded and one generation at a time.
        with engine_lock:
            result=generate(model,proc,prompt,max_tokens=192,temperature=0.5,verbose=False)
        text=extract_text(result)
    except Exception as exc:
        print('inference failed:',type(exc).__name__,str(exc),flush=True)
        raise HTTPException(503,'Local MLX inference failed') from exc
    if len(text)<4:raise HTTPException(502,'Qwen returned an empty or incomplete reply')
    return {'reply':text,'style_key':style_key,'style_used':label,'router_source':'rule_fallback',
            'reply_source':'qwen_lora_generated','needs_review':True,
            'quality_warnings':['يرجى مراجعة الصياغة قبل الإرسال؛ التصنيف محلي بقواعد وليس بفيصل.'],
            'generator':'Qwen3.5-4B + user-trained Saudi LoRA (MLX, local)',
            'faisal_loaded':False}
