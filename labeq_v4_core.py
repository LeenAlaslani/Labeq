"""Labeq V4: isolate response quality from style routing and add reviewed baselines.

This file is embedded into the Colab notebook; it is *not* a trained generator.
"""
import re
import unicodedata
from dataclasses import dataclass

SAUDI = {'صديق', 'صديقة', 'عائلة', 'قريب', 'قريبة', 'شخص آخر'}
WORK = {'مدير', 'عمل', 'عميل', 'جامعة'}
STYLE_NAME = {
    'polite':'لطيف', 'firm':'حازم', 'diplomatic':'دبلوماسي',
    'apology':'اعتذار', 'clarify':'طلب توضيح',
}
FOREIGN_PATTERNS = [
    r'(?<![\u0600-\u06ff])(?:عايز|عاوز|عايزة|عاوزة|عايزين|دلوقتي|دلوقت|ازاي|إزاي|أوي|حضرتك|فندم|متزعلش|هقدر|بقى)(?![\u0600-\u06ff])',
    r'(?<![\u0600-\u06ff])(?:بدي|بدك|هلق|هلأ|شو|هيك|منيح)(?![\u0600-\u06ff])',
]
UNNATURAL = [
    r'يا\s+(?:بطل|بيكي|جميلتي|أسطورة|عزيزي\s+الصديق)(?:\b|\s|[,،])',
    r'(?<!\w)(?:أنا\s+هنا\s+لمساعدتك|إليك\s+الرد|يمكنك\s+أن\s+تقول|سأقوم\s+بصياغة)(?!\w)',
    r'(?:ضمان\s+جودة\s+الأداء|الالتزام\s+بالجدول\s+الرسمي|لحسن\s+إدارتك\s+لوقتك)',
]

def norm(text):
    text = ''.join(c for c in str(text or '') if not unicodedata.combining(c))
    return re.sub(r'\s+', ' ', re.sub('[أإآ]', 'ا', text).replace('ى','ي').replace('ة','ه')).lower().strip()


def has(text, *tokens):
    return any(x in text for x in tokens)


@dataclass
class Brief:
    message: str
    relation: str
    goal: str
    intent: str
    style: str
    register: str
    speaker_gender: str
    recipient_gender: str


def intent_for(message, relation='', goal=''):
    """Conservative rules: infer an intent only where several contextual cues agree."""
    m, g = norm(message), norm(goal)
    context = m + ' ' + g
    if has(context,'مكالم','الاتصال','اقفل','انهي المكالم','يسولف','السوالف','سوالف') and has(context,'بنام','ابي انام','النوم','اقفل','انهي المكالم','انهاء المكالم','اطول','يطول','طوّل','اطول'):
        return 'end_call'
    if relation in ('مدير','عمل') and has(context,'الدوام','ساعات العمل','ساعات دوامي') and has(context,'خارج','بعد الدوام','بعد وقت','خارج ساعات','متكرر','كل مره','دوام اضافي'):
        return 'overtime'
    if has(context,'التصحيح','صحح','تصحيح الورقه','الدرجات') and has(context,'الخلف','ورقه','اعاده مراجعة','مراجعه التصحيح','حلي'):
        return 'recheck_grade'
    if has(context,'لا افهم','ما فهمت','مو واضح','تفاصيل','وضح','توضيح','استفسار') and has(context,'المطلوب','شغله','تكليف','ملف','جزء','الدكتوره','الدكتور','الاستاذ') and relation in ('مدير','جامعة','عمل'):
        return 'clarify_task'
    if has(context,'تأخرنا','تاخرنا','تاخر الرد','تأخر الرد') and relation == 'عميل':
        return 'client_delay'
    if relation == 'عميل' and has(context,'موعد','متى') and has(context,'ما اعرف','ما عندي','غير معروف','معلومه'):
        return 'unknown_eta'
    if has(context,'مهامه','شغله كل','شغله كل مره','يسند','استلم مهام','يطلب مني اسوي شغله') and relation in ('عمل','مدير'):
        return 'workload'
    if has(context,'مبلغ','فلوس','سلف','اقرض') and has(context,'ما اقدر','اعتذر','ارفض'):
        return 'decline_money'
    if has(context,'مراسله','رسائل','يرسل لي') and has(context,'يوقف','يوقف','توقف','طلبت'):
        return 'stop_messages'
    if has(context,'شكرا','شكر','مقدره','مقدر','وقفتها','وقفتك','ما قصرت') and has(context,'صديقت','صديق','وقف','مساعد','سند'):
        return 'thanks_friend'
    if (has(context,'طلعه','اطلع','ازور','زيارة','احضر') or re.search(r'(?<![ا-ي])اجي(?![ا-ي])',context)) and has(context,'مشغول','ما اقدر','اعتذر','مرتبط','مو فاضي') and relation in SAUDI:
        return 'decline_invitation'
    if has(context,'تأخرت','تاخرت','ما رديت','جرحت','جارح','ما حضرت','اخطأت','غلطت') and has(context,'اعتذر','اعتذار','اسف','زعلت'):
        return 'apology'
    return 'other'


def style_for(message, goal, intent, selected='تلقائي'):
    explicit = {'لطيف':'polite','حازم':'firm','دبلوماسي':'diplomatic','اعتذار':'apology','توضيح':'clarify', **{k:k for k in STYLE_NAME}}
    if selected in explicit:
        return explicit[selected]
    if intent in ('apology','client_delay'):
        return 'apology'
    if intent in ('clarify_task','recheck_grade','unknown_eta'):
        return 'clarify'
    if intent in ('overtime','workload','stop_messages'):
        return 'firm'
    if has(norm(goal),'حازم','حدود','ارفض بوضوح'):
        return 'firm'
    return 'polite'


def register_for(message,relation,style,override='تلقائي'):
    m=norm(message)
    if override=='سعودي يومي': return 'saudi'
    if override=='مهني بسيط': return 'professional'
    if 'رسمي' in m and not has(m,'مو رسمي','غير رسمي','بدون رسمي'):
        return 'professional'
    return 'professional' if relation in WORK else 'saudi'


def brief_for(message, relation, goal='', style='تلقائي', register='تلقائي',
              speaker_gender='غير محدد', recipient_gender='غير محدد'):
    intent=intent_for(message,relation,goal)
    return Brief(message.strip(),relation,goal.strip(),intent,style_for(message,goal,intent,style),
                 register_for(message,relation,style,register),speaker_gender,recipient_gender)


def curated(b):
    """Opt-in reliable baseline for widely repeated, unambiguous scenarios. Never invent specific promises."""
    m=norm(b.message)
    if b.intent == 'end_call':
        if 'حازم' == STYLE_NAME.get(b.style):
            return 'بنام الحين، نكمل سوالفنا بعدين.'
        return 'والله ودي أكمل سوالف معك، بس بنام الحين. نكمل بكرة؟' if has(m,'بنام','انام','النوم') else 'بقفّل الحين، نكمل سوالفنا بعدين؟'
    if b.intent == 'overtime':
        return 'أقدّر حاجة الفريق لإنجاز الشغل، لكن ما أقدر ألتزم بالعمل خارج الدوام بشكل متكرر. ممكن نرتّب الأولويات خلال ساعات العمل؟'
    if b.intent == 'recheck_grade':
        title='دكتورة' if has(m,'الدكتوره','دكتوره') else 'دكتور'
        return f'{title}، الحل موجود في الصفحة الخلفية من الورقة. ممكن تراجع التصحيح مرة ثانية؟' if has(m,'الخلف') else f'{title}، ممكن تراجع التصحيح مرة ثانية؟ ودي أتأكد من الدرجة.'
    if b.intent == 'clarify_task':
        if b.relation=='جامعة':
            if has(m,'الدكتوره','دكتوره'):
                return 'دكتورة، ممكن توضحين لي أي جزء يحتاج تعديل؟ أبغى أتأكد أني فهمت المطلوب.'
            if has(m,'الدكتور','دكتور'):
                return 'دكتور، ممكن توضح لي أي جزء يحتاج تعديل؟ أبغى أتأكد أني فهمت المطلوب.'
        return 'ممكن توضح لي المطلوب بالتحديد؟ أبغى أتأكد أني فهمته صح قبل أبدأ.'
    if b.intent == 'client_delay':
        return 'نعتذر عن تأخرنا في الرد، ونتفهم انزعاجك.'
    if b.intent == 'unknown_eta':
        return 'ما عندي موعد مؤكد للتوصيل حاليًا، وما أبي أعطيك وقت غير دقيق.'
    if b.intent == 'workload':
        return 'أقدر أساعدك بحدود وقتي، لكن ما أقدر أستلم مهامك كل مرة. خلّنا نتفق على توزيع واضح للشغل.'
    if b.intent == 'decline_money':
        return 'ودي أساعدك، بس للأسف ما أقدر أعطيك المبلغ.'
    if b.intent == 'stop_messages':
        return 'سبق وطلبت منك توقف المراسلة، وأرجو تحترم طلبي وما ترسل لي مرة ثانية.'
    if b.intent == 'thanks_friend':
        address = 'قصّرتي' if b.recipient_gender == 'مؤنث' or b.relation=='صديقة' else 'قصّرت'
        return 'شكرًا على وقفتك معي، والله ما '+address+'.' if address=='قصّرت' else 'شكرًا على وقفتك معي، والله ما قصّرتي.'
    if b.intent == 'decline_invitation':
        if has(m,'اليوم','الليله'):
            return 'ودي أجي، بس ما أقدر اليوم. إن شاء الله تتعوض.' if 'الليله' not in m else 'ودي أجي، بس ما أقدر الليلة. إن شاء الله تتعوض.'
        return 'ودي أجي، بس ما أقدر هالمرة. إن شاء الله تتعوض.'
    if b.intent == 'apology' and has(m,'ما رديت','رسالت'):
        return 'آسفة إني تأخرت عليك بالرد، أدري إن هالشي ضايقك.' if b.speaker_gender=='مؤنث' else ('آسف إني تأخرت عليك بالرد، أدري إن هالشي ضايقك.' if b.speaker_gender=='مذكر' else 'حقك علي، تأخرت عليك بالرد وأتفهم زعلك.')
    return None


def clean(text):
    s=str(text or '').strip()
    if '</think>' in s: s=s.split('</think>')[-1].strip()
    if '<think>' in s: return s  # flag in validation
    s=re.sub(r'^\s*(?:الرد\s+المقترح|الرسالة\s+المقترحة|صياغة\s+الرد|تقدر\s+تقول|ممكن\s+تقول|إليك\s+الرد)\s*[:：-]\s*','',s,flags=re.I)
    s=s.strip().strip('"«»“”').strip()
    return s


def validate(text,brief=None):
    t=clean(text)
    issues=[]
    if not t: return ['رد فارغ']
    if any(re.search(r,t,flags=re.I) for r in FOREIGN_PATTERNS): issues.append('تعبير غير سعودي واضح')
    if any(re.search(r,t,flags=re.I) for r in UNNATURAL): issues.append('صياغة آلية/متكلفة')
    if re.search(r'</?think>|<\|im_',t,flags=re.I): issues.append('رموز داخلية')
    if re.search(r'(?m)^\s*(?:\d+[.)]|[-*])\s+',t): issues.append('قائمة بدل رسالة')
    if len(t)>330: issues.append('الرد طويل')
    if t.count('\n')>2: issues.append('أسطر كثيرة')
    if len(t.split())<3: issues.append('الرد غير مكتمل')
    if brief:
        tn=norm(t)
        if brief.intent=='end_call':
            if not has(tn,'بنام','انام','النوم','بقفل','اقفل','بقفّل','انهي','نكمل','اكمل'):
                issues.append('ما يحقق هدف إنهاء المكالمة')
            if has(tn,'المكالمه الطويله','نضيع الوقت','ما ابي اكلمك','لا تتصل'):
                issues.append('الموقف تحوّل لرفض جارح')
        if brief.intent=='overtime':
            if not has(tn,'بعد الدوام','خارج الدوام','ساعات العمل','ساعات الدوام'):
                issues.append('ما يذكر حد ساعات العمل')
            if not has(tn,'ما اقدر','ما استطيع','لا استطيع','صعب علي','غير ممكن','مو ممكن'):
                issues.append('ما يضع حدًا واضحًا')
    return list(dict.fromkeys(issues))


def example_pairs(brief):
    if brief.register=='professional':
        return [
            ('مديري يطلب مني أداوم بعد الوقت كل يوم، أبي أوضح حدودي.', 'أقدّر الحاجة للشغل، لكن ما أقدر ألتزم بالعمل خارج الدوام بشكل متكرر. ممكن نرتب الأولويات خلال الدوام؟'),
            ('الدكتورة طلبت مني تعديل البحث وما فهمت أي جزء.', 'دكتورة، ممكن توضحين لي أي جزء يحتاج تعديل؟ أبغى أتأكد أني فهمت المطلوب.'),
            ('العميل زعلان من تأخر الرد.', 'نعتذر عن تأخرنا في الرد، ونتفهم انزعاجك.'),
        ]
    return [
        ('صاحبي يطوّل بالمكالمة وأنا أبي أنام.', 'والله ودي أكمل سوالف معك، بس بنام الحين. نكمل بكرة؟'),
        ('صديقتي تبغاني أطلع اليوم وأنا مشغولة.', 'ودي أطلع معك، بس ما أقدر اليوم. إن شاء الله تتعوض.'),
        ('صاحبي كل مرة يتأخر بدون ما يعلمني.', 'أبي أقول لك شي، تأخيرك كل مرة يعطلنا. ياليت تعلمني من بدري إذا بتتأخر.'),
    ]


def prompt_messages(b, previous=None, edit=None, bad_draft=None, problems=None, baseline=False):
    if baseline:
        sys=('أنت تكتب ردًا عربيًا قصيرًا جاهزًا لإرساله إلى شخص آخر بناء على موقف المستخدم. '
             'اجعل الرد طبيعيًا ومباشرًا. اكتب الرسالة فقط، لا تشرح.')
        user=f'الموقف: {b.message}\nالعلاقة: {b.relation}\nالهدف: {b.goal}\nالرد فقط:'
        return [{'role':'system','content':sys},{'role':'user','content':user}]
    gender=('بصيغة المتحدث المذكر' if b.speaker_gender=='مذكر' else
            'بصيغة المتحدث المؤنث' if b.speaker_gender=='مؤنث' else 'لا تفترض جنس المتحدث')
    other=('المخاطَب مذكر' if b.recipient_gender=='مذكر' else
           'المخاطَبة مؤنث' if b.recipient_gender=='مؤنث' else 'لا تفترض جنس المخاطَب')
    register=('سعودية يومية مفهومة، طبيعية وغير مصطنعة' if b.register=='saudi' else
              'سعودية مهنية بسيطة، بلا فصحى ثقيلة ولا عامية غير مناسبة')
    rules=(
        'أنت محرر رسائل سعودي. تكتب فقط الرسالة التي يرسلها صاحب الموقف إلى الشخص الآخر. '
        'لا تكلم المستخدم ولا تتقمص شخصية المستشار.\n'
        'نفّذ هدف صاحب الموقف حرفيًا ولا تقلب العلاقة أو المتحدث والمخاطَب.\n'
        'لا تبدأ بأهلًا أو يا بطل أو يا حبيبتي إذا كان الكلام استمرارًا لمحادثة.\n'
        'لهجة الرد: '+register+'. الأسلوب: '+STYLE_NAME[b.style]+'.\n'
        'التصريف: '+gender+'؛ '+other+'.\n'
        'عبارة إلى عبارتين قصيرتين غالبًا. استخدم كلمات بسيطة مثل «أبي، بس، ممكن» عند مناسبتها فقط.\n'
        'لا تستخدم: عزيزي، حضرتك، حبيبتي، يا بطل، لضمان جودة الأداء، الالتزام بالجدول الرسمي.\n'
        'لا تخترع أسبابًا، تواريخ، وعودًا، اجتماعات، اتفاقات، أو اعتذارات غير مطلوبة.\n'
        'لا تحول التماسًا بسيطًا إلى رفض قاس أو محاضرة. لا تكرر كلام السؤال.\n'
        'أخرج النص الجاهز للنسخ فقط؛ لا خيارات أو مقدمات أو علامات اقتباس.'
    )
    demonstration='\n\n'.join('الموقف: '+m+'\nالرد: '+a for m,a in example_pairs(b))
    user=(f'نماذج لدرجة العفوية المطلوبة (افهم أسلوبها ولا تنسخها):\n{demonstration}\n\n'
          f'الموقف الحالي: {b.message}\nالعلاقة: {b.relation}\nالهدف: {b.goal or "الرد على الموقف بلطف وبوضوح"}\n'
          f'نوع الرد: {STYLE_NAME[b.style]}\nالنية الأساسية: {b.intent}\nاكتب الرسالة فقط:')
    if previous and edit:
        user+=f'\nالرد السابق: {previous}\nتعديل المستخدم: {edit}\nأعد الصياغة من دون تغيير الحقائق.'
    if bad_draft and problems:
        user+=('\nالصياغة السابقة مرفوضة لأنها: '+', '.join(problems)+'\n'
              'الصياغة المرفوضة: '+bad_draft+'\nأعطني صياغة جديدة قصيرة، لا تعيد أي تعبير من المرفوضة.')
    return [{'role':'system','content':rules},{'role':'user','content':user}]


def is_edit(text,has_prior):
    if not has_prior:return False
    t=norm(text)
    return bool(re.match(r'^(?:(?:ممكن|ابي|ابغاك|تكفى)\s+)?(?:خله|خليه|خليها|خلها|اخليه|تخليه|تخليها|عدله|عدلها|اختصره|قصره|خليه|صيغه|اعيد|اعد|غير\s+الرد|غير\s+الصياغه|اقصر|الطف|رسمي|عامي|بدون\s+اعتذار|لا\s+تعتذر)',t))


def settings_from_edit(text,style,register):
    t=norm(text)
    if has(t,'الطف','خفيف','اهدا','بدون حزم'):
        style='لطيف'
    elif has(t,'حازم','اقوي','بوضوح اكثر'):
        style='حازم'
    if has(t,'رسمي','مهني') and not has(t,'مو رسمي','غير رسمي'):
        register='مهني بسيط'
    elif has(t,'سعودي','عامي','مو رسمي'):
        register='سعودي يومي'
    return style,register


def generate_with_model(model,tokenizer,messages,seed=None):
    import torch
    text=tokenizer.apply_chat_template(messages,tokenize=False,add_generation_prompt=True,enable_thinking=False)
    tokens=tokenizer(text,return_tensors='pt',add_special_tokens=False,truncation=True,max_length=2300)
    tokens={k:v.to(model.device) for k,v in tokens.items()}
    if seed is not None:
        torch.manual_seed(seed)
        if torch.cuda.is_available():torch.cuda.manual_seed_all(seed)
    with torch.inference_mode():
        result=model.generate(**tokens,max_new_tokens=115,do_sample=True,
                              temperature=0.7,top_p=0.8,top_k=20,repetition_penalty=1.08,
                              pad_token_id=tokenizer.pad_token_id,eos_token_id=tokenizer.eos_token_id)
    result=result[0, tokens['input_ids'].shape[-1]:]
    return clean(tokenizer.decode(result,skip_special_tokens=True))


def draft(model,tokenizer,b,mode='موجّه',previous=None,edit=None):
    if mode=='مرجعي':
        text=curated(b)
        if text is None: return None,'لا توجد صياغة مرجعية لهذا الموقف. اختاري «موجّه» لتوليد رد.'
        return text,'مرجعي: صياغة محددة مسبقًا، ليست ناتجة عن Qwen'
    if mode=='موجّه':
        text=curated(b)
        if text and not edit:
            return text,'مرجعي: سيناريو شائع؛ راجعي الرسالة قبل الإرسال'
    baseline=(mode=='Qwen الخام')
    last=None
    failures=[]
    for n in range(3 if not baseline else 1):
        prompts=prompt_messages(b,previous=previous,edit=edit,
                                bad_draft=last if failures else None,problems=failures,baseline=baseline)
        last=generate_with_model(model,tokenizer,prompts,seed=None)
        failures=validate(last,b)
        if baseline:
            return last, ('Qwen خام — للمقارنة فقط؛ ملاحظات آلية: '+', '.join(failures)) if failures else 'Qwen خام — بلا ملاحظات شكلية؛ الجودة غير مضمونة'
        if not failures:
            return last, 'Qwen موجّه: فحص آلي اجتاز الشكل وبعض قيود الموقف، وليس ضمان جودة'
    return None,'رفضنا عرض الرد بسبب: '+', '.join(failures)+'؛ جرّبي صياغة الهدف بشكل أوضح.'
