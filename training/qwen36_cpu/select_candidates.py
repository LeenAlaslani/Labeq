"""Compare genuine model selectors on fixed, unedited development candidates."""
import argparse,hashlib,json,random,sys,time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from labeq_engine import FAISAL_SYSTEM
from training.qwen36_cpu.planning import parse_plan

CONFIGURATIONS=['pilot_clean','pilot_fewshot','v2_clean','v2_fewshot']
QUESTION=(
    'أي رسالة جاهزة للإرسال تحقق كل ما طلبه المستخدم وتحفظ القيود والأدوار والجنس، '
    'بدون عذر أو معلومة أو وعد مخترع؟ يجب أن تكون سعودية طبيعية وسليمة لغويا، '
    'مع مهنية بسيطة في العمل والعميل. لا تختَر ردا ناقصا لمجرد أنه ألطف. '
    'إذا لم يصلح أي رد كما هو فاختر خيار عدم وجود رد صالح.'
)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--pool',type=Path,required=True)
    p.add_argument('--plans',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--selector',choices=['faisal','qwen36'],required=True)
    p.add_argument('--model');p.add_argument('--faisal',type=Path);p.add_argument('--space');p.add_argument('--source');args=p.parse_args()
    pool=json.loads(args.pool.read_text())['rows'];plans={r['case']['id']:r for r in json.loads(args.plans.read_text())}
    args.out.mkdir(exist_ok=False,parents=True);engine=client=api=space_info=None
    if args.selector=='faisal':
        from mlx_inference import MlxEngine
        engine=MlxEngine(args.model,None,args.faisal)
        if not engine.faisal_ready:raise RuntimeError('Actual original Faisal required')
        metadata={'selector':'faisal','base':args.model,'faisal_weights_sha256':hashlib.sha256((args.faisal/'adapter_model.safetensors').read_bytes()).hexdigest()}
    else:
        from huggingface_hub import HfApi,get_token
        from gradio_client import Client
        api=HfApi();space_info=api.space_info(args.space)
        if not space_info.private or args.space.split('/')[0]!=api.whoami()['name']:raise RuntimeError('Owned private diagnostic only')
        client=Client(args.space,token=get_token(),verbose=False,analytics_enabled=False)
        metadata=client.predict(api_name='/metadata')
        if metadata['source_commit']!=args.source:raise RuntimeError('Wrong private source')
    manifest={'study_source':__import__('subprocess').check_output(['git','rev-parse','HEAD'],text=True).strip(),
        'pool_sha256':hashlib.sha256(args.pool.read_bytes()).hexdigest(),'plans_sha256':hashlib.sha256(args.plans.read_bytes()).hexdigest(),
        'selector':args.selector,'metadata':metadata,'candidate_configurations':CONFIGURATIONS,'question':QUESTION}
    (args.out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2));results=[];rng=random.Random(20261122)
    for row in pool:
        case=row['case'];automatic=plans[case['id']]
        if automatic['case']!=case:raise ValueError('Plan case mismatch')
        plan=parse_plan(automatic['planning_result']['rows'][0]['reply'])
        names=CONFIGURATIONS.copy();rng.shuffle(names);options=[];mapping={}
        for index,name in enumerate(names):
            candidate=row['outputs'][name]
            if candidate['generation']['finish_reason']!='stop':raise ValueError('Incomplete candidate cannot be selected')
            label=chr(65+index);mapping[label]=name
            options.append({'label':label,'key':'candidate_'+str(index),'description':candidate['generation']['decoded_text']})
        options.append({'label':'E','key':'none','description':'لا يوجد رد صالح للإرسال كما هو؛ كل الردود تحتاج تعديل'})
        task={'state':{'الموقف':case['message'],'العلاقة':case['relation'],'الهدف':case['goal'],'automatic_advisory_plan':plan},'question':QUESTION,'options':options}
        messages=[{'role':'system','content':FAISAL_SYSTEM},{'role':'user','content':json.dumps(task,ensure_ascii=False,separators=(',',':'))}]
        started=time.monotonic();result={'case':case,'task':task,'anonymous_key':mapping}
        if engine:
            ids=engine.tokenizer.encode(engine.render(messages),add_special_tokens=False)
            option_ids=[engine.tokenizer.encode(x['label'],add_special_tokens=False) for x in options]
            if any(len(x)!=1 for x in option_ids):raise ValueError('Option letters must be single tokens')
            with engine.select('faisal'):
                output=engine.model.language_model(engine.mx.array([ids]))
                scores=output.logits[0,-1,engine.mx.array([x[0] for x in option_ids])]
                choice=options[int(engine.mx.argmax(scores).item())]['label'];result['option_logits']=scores.tolist()
        else:
            if api.space_info(args.space).sha!=space_info.sha:raise RuntimeError('Private source changed')
            response=client.predict({'rows':[{'id':case['id'],'messages':messages}],'sampler':'greedy'},api_name='/check')
            result['raw_selector_response']=response;choice=response['rows'][0]['reply'].strip()
        result['choice']=choice;result['selected_configuration']=mapping.get(choice)
        result['selected_reply']=row['outputs'][mapping[choice]]['generation']['decoded_text'] if choice in mapping else None
        result['seconds']=round(time.monotonic()-started,3);results.append(result)
        (args.out/'responses.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
        print(json.dumps({'id':case['id'],'choice':choice,'selected':mapping.get(choice),'reply':result['selected_reply']},ensure_ascii=False),flush=True)


if __name__=='__main__':main()
