"""Preserve approved completions and build an explicitly synthetic long-form experiment."""
import argparse,hashlib,json,random,statistics
from pathlib import Path

HERE=Path(__file__).resolve().parent


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def prompt(message,relation,goal,style,system):
    return [{'role':'system','content':system},{'role':'user','content':f'الموقف: {message}\nالعلاقة: {relation}\nالهدف: {goal}\nالأسلوب: {style}\nاكتب الرسالة للطرف الآخر، واحفظ كل الطلبات والقيود بدون اختصار يضيع المعنى.'}]


def migrate(row,system):
    fields=dict(line.split(': ',1) for line in row['prompt'][1]['content'].splitlines() if ': ' in line)
    return {'prompt':prompt(fields['الموقف'],fields['العلاقة'],fields['الهدف'],fields['الأسلوب'],system),'completion':row['completion']}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--approved-data',type=Path,required=True);p.add_argument('--out',type=Path,required=True);args=p.parse_args()
    policy=HERE/'policy.json';system=json.loads(policy.read_text())['system']
    gold_path=args.approved_data/'train_gold_178.jsonl';val_path=args.approved_data/'validation_114.jsonl'
    gold=[json.loads(x) for x in gold_path.read_text().splitlines() if x.strip()]
    val=[json.loads(x) for x in val_path.read_text().splitlines() if x.strip()]
    synthetic_path=HERE/'synthetic.json';synthetic=json.loads(synthetic_path.read_text())['rows']
    if len(gold)!=178 or len(val)!=114 or len(synthetic)!=80:raise ValueError('Unexpected source counts')
    train=[]
    for i,row in enumerate(gold):
        migrated=migrate(row,system)
        if migrated['completion']!=row['completion']:raise ValueError('Approved completion changed')
        train.append({**migrated,'provenance':f'approved_completion_{i+1}; prompt_contract_updated'})
    messages=[]
    for family,relation,goal,message,reply in synthetic:
        if not all(isinstance(x,str) and x.strip() for x in [family,relation,goal,message,reply]):raise ValueError('Malformed synthetic row')
        if len(reply.split())<18:raise ValueError('Short synthetic reference: '+family)
        messages.append(message)
        styles=['عفوي','واضح','مهني','عفوي'] if relation in {'عمل','جامعة','عميل'} else ['عفوي','واضح','عفوي','واضح']
        for repeat,style in enumerate(styles):train.append({'prompt':prompt(message,relation,goal,style,system),'completion':[{'role':'assistant','content':reply}],'provenance':f'AI_authored_{family}; writing_style={style}; view_{repeat+1}'})
    if len(set(messages))!=80:raise ValueError('Duplicate synthetic situation')
    protected=[]
    for name in ['dev.json','regressions.json','cpu_candidate_holdout.json']:
        data=json.loads((HERE.parent/'generalization'/name).read_text());protected.extend(data['cases'] if isinstance(data,dict) else data)
    train_messages={r['prompt'][1]['content'].splitlines()[0].removeprefix('الموقف: ') for r in train}
    if train_messages & {r['message'] for r in protected}:raise ValueError('Exact protected-case overlap')
    random.Random(3407).shuffle(train);args.out.mkdir(parents=True,exist_ok=False)
    for name,rows in [('train.jsonl',train),('validation.jsonl',[migrate(r,system) for r in val])]:
        (args.out/name).write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows))
    manifest={'approved_completion_count':178,'approved_completions_preserved_verbatim':True,'synthetic_unique':80,'synthetic_views_per_situation':4,'writing_views':'عفوي/واضح for every case; مهني additionally for work, university and customers; repeated views explicit','training_rows':len(train),'unique_training_prompts':len({json.dumps(r['prompt'],ensure_ascii=False) for r in train}),'seed':3407,'synthetic_median_words':statistics.median(len(r[4].split()) for r in synthetic),'validation_rows':114,'no_exact_protected_case_overlap':True,'independent_human_review':False,'limitations':'Assistant-authored and curated references, not approved gold. Exact-string overlap prevention is not a semantic contamination guarantee. Lower validation loss is not a quality score.','sha256':{str(path):digest(path) for path in [gold_path,val_path,policy,synthetic_path,args.out/'train.jsonl',args.out/'validation.jsonl',HERE.parent/'generalization/cpu_candidate_holdout.json']}}
    (args.out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2));print(json.dumps(manifest,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
