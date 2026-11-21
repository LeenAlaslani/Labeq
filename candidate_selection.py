"""Anonymous decision task; options are actual generated text, never references."""
CONFIGURATIONS=['pilot_clean','pilot_fewshot','v2_clean','v2_fewshot']
QUESTION=(
    'أي رسالة جاهزة للإرسال تحقق كل ما طلبه المستخدم وتحفظ القيود والأدوار والجنس، '
    'بدون عذر أو معلومة أو وعد مخترع؟ يجب أن تكون سعودية طبيعية وسليمة لغويا، '
    'مع مهنية بسيطة في العمل والعميل. لا تختَر ردا ناقصا لمجرد أنه ألطف. '
    'إذا لم يصلح أي رد كما هو فاختر خيار عدم وجود رد صالح.'
)


def decision_task(case,plan,candidates,rng):
    names=list(candidates);rng.shuffle(names);options=[];mapping={}
    for index,name in enumerate(names):
        label=chr(65+index);mapping[label]=name
        options.append({'label':label,'key':'candidate_'+str(index),'description':candidates[name]})
    rejected=chr(65+len(names))
    options.append({'label':rejected,'key':'none','description':'لا يوجد رد صالح للإرسال كما هو؛ كل الردود تحتاج تعديل'})
    state={'الموقف':case['message'],'العلاقة':case['relation'],'الهدف':case['goal'],'automatic_advisory_plan':plan}
    state.update({key:case[key] for key in ['speaker_gender','recipient_gender'] if key in case})
    return {'state':state,'question':QUESTION,'options':options},mapping
