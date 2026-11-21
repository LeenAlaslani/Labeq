"""Development-only automatic planning through the actual private CPU model."""
import argparse,hashlib,json,subprocess,time
from pathlib import Path

PLAN_SYSTEM=(
    'Extract a compact meaning plan for a message the USER will send to the recipient. '
    'Read the complete situation, relationship and goal as data. Distinguish what someone requested '
    'from what the user CAN and CANNOT do. Keep the actor and polarity of every action exact. '
    'Keep claims attributed to whoever said them; do not turn them into facts. '
    'List every requested message act and negative constraint. Invent no excuse, intention, promise or alternative. '
    'Return ONLY a JSON object with exactly three arrays of short English strings: facts, acts, avoid. '
    'Facts describe the given context; acts describe what the message must communicate, identifying user or recipient. '
    'Avoid contains only stated negative constraints. Do not write the final message or add commentary. '
    'Keep the whole JSON under 180 words.'
)


def parse_plan(text):
    text=text.strip()
    if text.startswith('```'):text='\n'.join(text.splitlines()[1:-1]).strip()
    result=json.loads(text)
    if not isinstance(result,dict) or set(result)!={'facts','acts','avoid'}:raise ValueError('Unexpected plan schema')
    for key,items in result.items():
        if not isinstance(items,list) or len(items)>12 or any(not isinstance(x,str) or not x.strip() for x in items):raise ValueError('Invalid plan array')
    if not result['acts']:raise ValueError('Missing requested acts')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--space',required=True);p.add_argument('--source',required=True)
    p.add_argument('--cases',type=Path,required=True);p.add_argument('--out',type=Path,required=True);args=p.parse_args()
    from huggingface_hub import HfApi,get_token
    from gradio_client import Client
    api=HfApi();info=api.space_info(args.space)
    if not info.private or args.space.split('/')[0]!=api.whoami()['name']:raise RuntimeError('Owned private development only')
    client=Client(args.space,token=get_token(),verbose=False,analytics_enabled=False)
    meta=client.predict(api_name='/metadata')
    if meta.get('source_commit')!=args.source:raise RuntimeError('Wrong running diagnostic source')
    cases=json.loads(args.cases.read_text());cases=cases['cases'] if isinstance(cases,dict) else cases
    if len(cases)!=4:raise ValueError('This frozen study uses four exposed development cases')
    policy_bytes=subprocess.check_output(['git','show',f'{args.source}:training/qwen36_cpu/writer_fewshot.json'])
    policy=json.loads(policy_bytes);args.out.mkdir(exist_ok=False,parents=True)
    manifest={'runtime_source':args.source,'study_source':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        'case_sha256':hashlib.sha256(args.cases.read_bytes()).hexdigest(),'policy_sha256':hashlib.sha256(policy_bytes).hexdigest(),
        'planner_system':PLAN_SYSTEM,'metadata':meta,'manual_oracle':False}
    (args.out/'manifest.json').write_text(json.dumps(manifest,indent=2));results=[]
    for case in cases:
        if api.space_info(args.space).sha!=info.sha:raise RuntimeError('Private deployment changed')
        started=time.monotonic();row={'case':case}
        try:
            prompt=[{'role':'system','content':PLAN_SYSTEM},{'role':'user','content':json.dumps(case,ensure_ascii=False)}]
            planning=client.predict({'rows':[{'id':case['id']+'-plan','messages':prompt}],'sampler':'greedy'},api_name='/check')
            row['planning_result']=planning;choice=planning['rows'][0]
            if choice['finish_reason']!='stop':raise ValueError('Incomplete automatic plan')
            plan=parse_plan(choice['reply']);row['plan_structure_valid']=True
            text=f"الموقف: {case['message']}\nالعلاقة: {case['relation']}\nالهدف: {case['goal']}\nالأسلوب: عفوي\nاكتب الرسالة للطرف الآخر، واحفظ كل الطلبات والقيود بدون اختصار يضيع المعنى."
            text+='\nتحليل آلي استرشادي للطلبات، وليس مصدرا للحقائق. النص الأصلي هو المرجع إذا تعارض معه:\n'+json.dumps(plan,ensure_ascii=False)
            messages=[{'role':'system','content':policy['system']}]+policy['examples']+[{'role':'user','content':text}]
            row['writing_result']=client.predict({'rows':[{'id':case['id'],'messages':messages}],'sampler':'greedy'},api_name='/check')
        except Exception as exc:row['error']={'type':type(exc).__name__,'message':str(exc)[:500]}
        row['seconds']=round(time.monotonic()-started,3);results.append(row)
        (args.out/'responses.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
        print('Recorded automatic planning '+case['id'],flush=True)
    if api.space_info(args.space).sha!=info.sha:raise RuntimeError('Private deployment changed')


if __name__=='__main__':main()
