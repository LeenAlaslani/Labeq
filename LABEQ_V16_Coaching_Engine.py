"""LABEQ V16: context-grounded communication planning and guided generation.

Hot-install in the already running Colab process AFTER loading Qwen/LoRA/Faisal:

    from google.colab import files
    uploaded = files.upload()
    exec(uploaded['LABEQ_V16_Coaching_Engine.py'].decode('utf-8'))

This wraps the existing engine class. The installed Qwen3.5 and Faisal adapters
are NOT modified or retrained. The planner and reviewer use the Qwen base model
with adapters disabled; the actual response uses the Saudi LoRA. Quality is
heuristic/model-reviewed, not externally validated or guaranteed.
"""
from __future__ import annotations

from difflib import SequenceMatcher
import re

from LABEQ_V15_Goal_Fix import alignment_flags, brief_for, intent_guidance
from saudi_register import (
    SAUDI_EXAMPLES, SAUDI_SYSTEM, clean_writing, explicit_fusha,
    register_instruction, register_warnings,
)


def _clean(s):
    return re.sub(r"\s+", " ", str(s or "")).strip()


def _field(text, labels):
    for line in (text or "").splitlines():
        line = line.strip().lstrip("-• ")
        for label in labels:
            found = re.match(rf"^(?:{re.escape(label)})\s*[:：-]\s*(.+)$", line)
            if found:
                return _clean(found.group(1))[:180]
    return ""


def parse_plan(text):
    """Read a compact plan; never invent a value when the model omits it."""
    return {
        "core": _field(text, ("جوهر الموقف", "الجوهر", "المشكلة")),
        "objective": _field(text, ("الهدف", "المطلوب")),
        "strategy": _field(text, ("الخطوة", "الاستراتيجية", "الطريقة")),
        "risk": _field(text, ("انتبهي", "الخطر", "احذري")),
    }


def style_instruction(style, goal, message):
    # Style describes HOW to say it, never replaces WHAT the user needs.
    defaults = {
        "polite": "لبق: ابدئي بتفهم قصير، ثم قولي المقصود بوضوح دون تلميحات مبهمة.",
        "firm": "حازم محترم: قولي قرارًا واضحًا وحدودًا قابلة للفهم بلا تبرير زائد أو تهديد.",
        "diplomatic": "دبلوماسي: اعترفي باختلاف وجهات النظر وافتحي مساحة للتفاهم، دون التنازل عن الهدف الأصلي.",
        "clarify": "طلب توضيح: ابدئي بسؤال مباشر عن سبب سوء الفهم أو عن المقصود، حسب الحالة. اربطي السؤال بهدف المستخدم.",
        "apology": "اعتذار: اعتذري عن تصرف خاطئ إذا ذكره المستخدم، وإلا فلا تعترفي بخطأ غير مثبت؛ يمكنك الاعتذار عن عدم التمكن فقط إذا كان مناسبًا.",
        "formal": "مهني رسمي: لغة عمل سعودية واضحة بلا تكلف ولا إطالة.",
        "مختصر": "مختصر: احفظي معنى الموقف والهدف حتى لو قلّ عدد الكلمات.",
    }
    if style in defaults: return defaults[style]
    return defaults["polite"]


def _style_key(style, fallback):
    if style == "تلقائي": return fallback
    return {"لبق":"polite","لطيف":"polite","عفوي":"polite","واضح":"firm","حازم":"firm",
        "دبلوماسي":"diplomatic","اعتذار":"apology","طلب توضيح":"clarify", "رسمي":"formal", "مختصر":"مختصر"}.get(style,"polite")


def _style_display(key):
    return {"polite":"لبق","firm":"حازم","diplomatic":"دبلوماسي","apology":"اعتذار",
            "clarify":"طلب توضيح","formal":"رسمي","مختصر":"مختصر"}.get(key,"لبق")


def _get_last_assistant(history):
    for item in reversed(history or []):
        if item.get("role") == "assistant": return str(item.get("content", ""))[:500]
    return ""


def _get_instructions(history):
    return "\n".join(
        item["content"][:500] for item in history or []
        if item.get("role") == "user" and item.get("content", "").startswith("تعليمات تعديل الرد:")
    )


def local_warnings(reply, message, goal, style, last_reply=""):
    flags=[]
    text=_clean(reply)
    if len(text)<22:flags.append("الصياغة قصيرة جدًا وقد لا توصل الهدف")
    if len(text)>450:flags.append("الرد طويل على رسالة محادثة")
    if re.search(r"(?:تقدرين تقولين|تقدرين تقول|يمكنك الرد|الرد المقترح|كذكاء اصطناعي)",text):
        flags.append("الرد تعليمات للمستخدم بدل رسالة للطرف الآخر")
    if text.startswith("اعتذري") and re.search(r"(?:أبي\s+أعتذر|أعتذر عن|أبغى\s+أعتذر)", message + " " + goal):
        flags.append("الرد يطلب من المستخدم الاعتذار بدل كتابة اعتذاره للطرف الآخر")
    if re.search(r"(?:صرخت|ضربت|أهنت|كذبت عليك|خنتك)",text) and not re.search(r"(?:صرخ|ضرب|أهان|كذب|خان|خنت)",message):
        flags.append("الرد قد ينسب للمستخدم خطأ غير مذكور")
    if style == "clarify" and not re.search(r"؟|\?|(?:^|\s)(?:وش|إيش|ايش|هل|ممكن)(?:\s|$)", text):
        flags.append("صياغة طلب التوضيح تحتاج سؤالًا محددًا للطرف الآخر")
    if last_reply and SequenceMatcher(None,_clean(last_reply),text).ratio() > 0.88:
        flags.append("الصياغة الجديدة تشبه الرد السابق جدًا ولم تتغير بشكل مفيد")
    if re.search(r"(?:إني|أني)\s+(?:بأتابع|بتابع|براجع)|أبي\s+أتابع", message):
        if not re.search(r"(?:أتابع|بتابع|نتابع|بنتابع|أراجع|براجع|نراجع|بنراجع)", text):
            flags.append("الرد أغفل متابعة الموضوع التي طلب المستخدم توضيحها")
    return flags


def _parse_review(text):
    """Base-model reviewer signals: uncertain outputs are not a pass."""
    t=(text or "").strip()
    if re.search(r"(?:^|\n)\s*(?:النتيجة|الحكم)\s*[:：]\s*(?:غير مناسب|يحتاج تعديل)",t):
        return False, _field(t,("السبب", "المشكلة")) or "المراجعة رصدت ضعفًا في الصياغة"
    if re.search(r"(?:^|\n)\s*(?:النتيجة|الحكم)\s*[:：]\s*مناسب",t):
        return True,""
    return None,""


def reply_v16(self, message, relation="صديق", goal="أبي رد مناسب وواضح",
              style="تلقائي", speaker_gender="غير محدد", recipient_gender="غير محدد",
              history=None, generation_mode="موجّه"):
    message=_clean(message);relation=_clean(relation);goal=_clean(goal)
    if not message:raise ValueError("اكتبي الموقف أولًا")
    if len(message)>2000:raise ValueError("الموقف طويل جدًا")
    from labeq_engine import ALLOWED_USER_STYLES, quality_flags
    if style not in ALLOWED_USER_STYLES:raise ValueError("أسلوب غير مدعوم")
    self.load()
    if style=="تلقائي":
        selected,router_source=self.predict_style(message,relation,goal)
    else:
        selected,router_source=None,"user_selected"
    style_key=_style_key(style,selected or "polite")
    previous=_get_last_assistant(history)
    modifier=_get_instructions(history)
    # Phase 1: grounded short brief using the base model; this is NOT Faisal's explanation.
    plan_prompt=(
        "أنتِ مستشارة تواصل سعودية. لخصي بكلام سعودي بسيط ما قاله المستخدم فقط، دون افتراض مشاعر أو أخطاء أو وعود. "
        "حددي مين اللي تأخر أو غلط بدقة، ولا تعكسي الأدوار. اجمعي الطلبات والقيود من نص الموقف كله. "
        "اكتبي أربع سطور قصيرة بهذه التسميات بالضبط، ولا تكتبي رسالة الرد:\n"
        "جوهر الموقف: [المشكلة المحددة كما وردت]\n"
        "الهدف: [ما الذي يريد تحقيقه فعلاً]\n"
        "الخطوة: [التصرف التواصلي الذي يحقق الهدف دون تصعيد]\n"
        "انتبهي: [تفسير خاطئ واحد يجب تجنبه]\n"
        f"الموقف: {message}\nالعلاقة: {relation}\nهدف المستخدم: {goal}"
    )
    plan_raw=self._one_generation([{"role":"user","content":plan_prompt}],use_adapter=False)
    plan=parse_plan(plan_raw)
    # Phase 2: real response by Saudi LoRA. Keep the user's facts as the source of truth.
    register = register_instruction(relation, style_key, modifier)
    gen_system = SAUDI_SYSTEM + "\n" + register
    examples = [] if explicit_fusha(modifier) else [dict(item) for item in SAUDI_EXAMPLES]
    style_line=style_instruction(style_key,goal,message)
    brief = brief_for(message, goal, relation)
    def gen_prompt(extra=""):
        return (
            f"الموقف: {message}\nالعلاقة: {relation}\nالهدف: {goal}\n"
            f"الأسلوب: {_style_display(style_key)}\n"
            f"{style_line}\nجنس المتحدث: {speaker_gender}، جنس المخاطب: {recipient_gender}.\n"
            f"{intent_guidance(brief)}\n"
            # The generated coaching plan is advisory; it must not introduce facts into the draft.
            + f"طريقة الكتابة: {register}\n"
            + (f"{modifier}\n" if modifier else "")
            + (f"ملاحظة للمراجعة: {extra}\n" if extra else "")
            + "اكتبي نص الرسالة السعودية للطرف الآخر مباشرة. الرسالة فقط."
        )
    def generate(extra="", retry=False):
        return clean_writing(self._one_generation(
            [{"role":"system","content":gen_system}] + examples
            + [{"role":"user","content":gen_prompt(extra)}], retry=retry,
        ), modifier)
    first=generate()
    def check(candidate):
        return list(dict.fromkeys(
            local_warnings(candidate, message, goal, style_key, previous)
            + quality_flags(candidate, relation, goal, message)
            + alignment_flags(candidate, brief)
            + register_warnings(candidate, modifier)
        ))
    # Phase 3: semantic reviewer on Qwen base. The same model is NOT an independent guarantee.
    def review(candidate):
        prompt = (
            "قيّمي الرسالة الآتية مقابل طلب المستخدم، لا تجاملي. "
            "هل تحافظ على الهدف الأصلي والأسلوب المطلوب دون اختلاق أسباب أو وعود؟ "
            "احكمي على كل طلب وقيد في الموقف، وليس عنوان الهدف فقط. "
            "لا تطلبي وعدا جديدا لم يطلبه الشخص، ولا تعتبري الاعتذار عن خطأ مذكور مشكلة. "
            "لا تعتبري كلمة بس نقصا في الحزم، ولا تعتبري الاعتذار كلمة غير سعودية بحد ذاتها. "
            "لا تضيفي شروطا مثل ذكر سبب أو وعد بموعد تعويض إذا لم يطلبها المستخدم. "
            f"طريقة الكتابة المطلوبة: {register}\n"
            "اكتبي سطرين فقط: النتيجة: مناسب أو غير مناسب. "
            "السبب: [سبب محدد في أقل من 15 كلمة].\n"
            f"الموقف: {message}\nالعلاقة: {relation}\nالهدف: {goal}\n"
            f"النبرة: {_style_display(style_key)}\nالرسالة: {candidate}"
        )
        return _parse_review(self._one_generation([{"role":"user","content":prompt}], use_adapter=False))

    flags = check(first)
    # A fallible style opinion must not automatically rewrite a grounded draft.
    # Concrete register/intent diagnostics drive the bounded rewrite; the model's
    # remaining concerns are still returned to the user as review warnings.
    was_retried = bool(flags)
    reviewed, issue = review(first)
    if reviewed is False:
        flags.append(issue)
    if was_retried:
        try:
            reason = "؛ ".join(flags)
            revised = generate("أصلحي الملاحظات التالية: " + reason, retry=True)
            if revised.strip():
                new_flags = check(revised)
                new_review, new_issue = review(revised)
                if new_review is False:
                    new_flags.append(new_issue)
                if not first.strip() or (new_review is not False and len(new_flags) < len(flags)):
                    first, flags, reviewed = revised, new_flags, new_review
        except Exception:
            pass
    if not first.strip():raise RuntimeError("المودل لم يولد ردًا")
    coach={k:v for k,v in plan.items() if v}
    return {
        "reply":first.strip(),"style_used":_style_display(style_key),"router_source":router_source,
        "reply_source":"qwen_lora_generated", "style_key":style_key if style_key in {"polite","firm","diplomatic","apology","clarify"} else (selected or "polite"),
        "generator":self.generator if hasattr(self, "generator") else "Qwen3.5-4B + Saudi LoRA",
        "coaching":coach,"review_status":"flagged" if flags else ("model_reviewed" if reviewed else "unverified"),
        "needs_review":bool(flags), "quality_warnings":list(dict.fromkeys(flags)),"was_retried":was_retried,
    }



def install(engine=None):
    import labeq_engine as mod
    cls=mod.LabeqEngine
    if getattr(cls,"_labeq_v16_installed",False):
        print("✅ LABEQ V16 مثبت مسبقًا")
        return

    cls.reply=reply_v16
    cls._labeq_v16_installed=True
    print("✅ V16: Context plan → Saudi LoRA response → model review, preserving actual Faisal routing")
    print("ℹ️ Improvement in pipeline, NOT a new fine-tuning or proof of quality. Test with real scenarios.")
    if engine is not None:
        print("Qwen loaded:",bool(getattr(engine,'model',None) is not None))
        print("Faisal loaded:",bool(getattr(engine,'faisal_ready',False)))

if __name__ == "__main__" or "engine" in globals():
    install(globals().get("engine"))
