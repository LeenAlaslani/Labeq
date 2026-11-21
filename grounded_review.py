"""Source IDs prevent the reviewer from substituting draft quotes for user evidence.

These are source units, not a claim to have extracted every atomic intention.
The model's judgments remain fallible and require independent evaluation.
"""
import json
import re

REVIEW_MARKER='LABEQ_SOURCE_ID_REVIEW\n'


def source_units(message,goal):
    if goal.strip() and len(goal.strip())<4:
        return {'r0':message+'\n'+goal}
    parts=[x.strip() for x in re.findall(r'[^.!؟،,;\n]+(?:[.!؟،,;\n]+|$)',message) if x.strip()]
    if not parts or len(parts)>11 or any(len(x)<4 for x in parts):parts=[message]
    parts=list(dict.fromkeys(parts))
    if goal.strip() and goal not in parts:parts.append(goal)
    return {f'r{i}':text for i,text in enumerate(parts)}


def id_review_prompt(message,relation,goal,candidate,register):
    return REVIEW_MARKER+json.dumps({'sources':source_units(message,goal),'relationship':relation,'candidate':candidate,'register':register},ensure_ascii=False)


def review_schema(sources):
    item={'type':'object','properties':{'status':{'type':'string','enum':['met','missing','contradicted']},'reason':{'type':'string'}},'required':['status','reason'],'additionalProperties':False}
    issue={'type':'object','properties':{'quote':{'type':'string'},'reason':{'type':'string'}},'required':['quote','reason'],'additionalProperties':False}
    return {'type':'object','properties':{'checks':{'type':'object','properties':{key:item for key in sources},'required':list(sources),'additionalProperties':False},'unsupported':{'type':'array','items':{'type':'string'},'maxItems':8},'language_issues':{'type':'array','items':issue,'maxItems':8}},'required':['checks','unsupported','language_issues'],'additionalProperties':False}


def attach_source_quotes(raw,sources):
    data=json.loads(raw)
    if not isinstance(data,dict) or set(data)!={'checks','unsupported','language_issues'}:
        raise ValueError('Invalid source-ID review schema')
    if not isinstance(data['checks'],dict) or set(data['checks'])!=set(sources):
        raise ValueError('Every source ID must be reviewed exactly once')
    checks=[]
    for key,quote in sources.items():
        value=data['checks'][key]
        if not isinstance(value,dict) or set(value)!={'status','reason'}:
            raise ValueError('Invalid source-ID check')
        checks.append({'source_quote':quote,**value})
    return json.dumps({'checks':checks,'unsupported':data['unsupported'],'language_issues':data['language_issues']},ensure_ascii=False)
