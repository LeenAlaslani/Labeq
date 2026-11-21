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

from semantic_review import parse_review, review_prompt
from difflib import SequenceMatcher
import re

from saudi_register import (
    SAUDI_EXAMPLES, SAUDI_SYSTEM, clean_writing, explicit_fusha,
    normalize_saudi, register_instruction, register_warnings, writing_style,
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
        "polite": "نبرة لطيفة ومحترمة. حافظ على كل ما طلبه الشخص، ولا تضف اعتذارا أو وعدا أو طلبا من عندك.",
        "firm": "نبرة واضحة وثابتة باحترام. التزم بنفس حدود المستخدم ونطاقها ومدتها؛ لا تخترع حصة مساعدة أو موعدا أو بديلا.",
        "diplomatic": "نبرة هادئة ومراعية للعلاقة. نفذ مقصد المستخدم كامل بدون افتراض اختلاف آراء أو استبدال طلبه بحوار عام.",
        "clarify": "نبرة استيضاح مهذبة. اطلب نفس التوضيح أو الإجراء اللي يريده المستخدم، ولا تحول طلب تنفيذ إجراء إلى سؤال عن سببه.",
        "apology": "نبرة صادقة ومراعية للأثر. إذا طلب الشخص الاعتذار فاكتب اعتذاره هو، واحفظ تحمله للمسؤولية وحدوده؛ لا تنسب له خطأ أو عذرا غير مذكور.",
        "formal": "نبرة سعودية مهنية ومحترمة، واضحة وطبيعية بدون تكلف، مع حفظ كامل المقصد.",
        "مختصر": "صياغة مختصرة تحفظ كل المطلوب والقيود؛ لا تختصر على حساب المعنى.",
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
    if style == "clarify" and re.search(r"ممكن\s+أ(?:وضح|شرح)\s+لي", text):
        flags.append("السؤال خلط بين المتحدث والمخاطب؛ اطلب من الطرف الآخر هو يوضح لك المطلوب")
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
    coaching_error = None
    try:
        plan_raw=self._one_generation([{"role":"user","content":plan_prompt}],use_adapter=False,max_tokens=256)
    except Exception as exc:
        plan_raw=""
        coaching_error=type(exc).__name__
    plan=parse_plan(plan_raw)
    # Phase 2: real response by Saudi LoRA. Keep the user's facts as the source of truth.
    register = register_instruction(relation, style_key, modifier)
    gen_system = getattr(self, "writer_system", SAUDI_SYSTEM)
    selected_examples = getattr(self, "writer_examples", SAUDI_EXAMPLES)
    examples = [] if explicit_fusha(modifier) else [dict(item) for item in selected_examples]
    style_line=style_instruction(style_key,goal,message)
    def gen_prompt(extra="", reference=""):
        prompt = (
            f"الموقف: {message}\nالعلاقة: {relation}\nالهدف: {goal}\n"
            f"الأسلوب: {writing_style(style_key, modifier)}\n"
            "اكتب الرسالة للطرف الآخر، واحفظ كل الطلبات والقيود بدون اختصار يضيع المعنى."
        )
        # Faisal's selected action controls tone; original facts and all user
        # requirements stay authoritative, including for a manual override.
        prompt += f"\nطريقة التواصل: {_style_display(style_key)}\n{style_line}"
        if speaker_gender != "غير محدد":
            prompt += f"\nجنس المتحدث: {speaker_gender}"
        if recipient_gender != "غير محدد":
            prompt += f"\nجنس المخاطب: {recipient_gender}"
        if modifier:
            prompt += f"\n{modifier}\nطريقة الكتابة: {register}"
        if reference:
            prompt += (
                "\nنص سابق مطلوب تعديل صياغته فقط، وليس مصدرا للحقائق؛ الموقف والهدف هما الأصل:\n"
                + reference
            )
        if extra:
            prompt += f"\nملاحظة للمراجعة: {extra}"
        return prompt
    def generate(extra="", retry=False, reference=""):
        raw = clean_writing(self._one_generation(
            [{"role":"system","content":gen_system}] + examples
            + [{"role":"user","content":gen_prompt(extra, reference or (previous if modifier else ""))}], retry=retry, max_tokens=256,
        ), modifier)
        text, edits = normalize_saudi(raw, modifier, message + " " + goal)
        return {"reply":text,"draft_before_register_normalization":raw,"register_normalization":edits}
    selected_record=generate()
    first=selected_record["reply"]
    def check(candidate):
        return list(dict.fromkeys(
            local_warnings(candidate, message, goal, style_key, previous)
            + quality_flags(candidate, relation, goal, message)
            + register_warnings(candidate, modifier)
        ))
    # A grounded failure triggers repair regardless of the words used in its reason.
    # This is same-family model feedback, not independent semantic validation.
    def review(candidate):
        prompt = review_prompt(message, relation, goal, candidate, register)
        raw = self._one_generation([{"role":"user","content":prompt}], use_adapter=False, max_tokens=640)
        return parse_review(raw, message, goal, candidate)

    def assess(candidate):
        hard = check(candidate)
        try:
            judgment = review(candidate)
        except Exception as exc:
            judgment = {"valid":False,"checks":[],"unsupported":[],"issues":[],
                        "error":"review_generation_failed","error_type":type(exc).__name__}
        issues = list(dict.fromkeys(hard + judgment["issues"]))
        return hard, judgment, issues

    hard, judgment, flags = assess(first)
    attempts = [{**selected_record, "review":judgment, "warnings":flags}]
    was_retried = bool(flags)
    retry_error = None
    if was_retried:
        try:
            revised_record = generate("أصلح الملاحظات مع حفظ كل قيود النص الأصلي: " + "؛ ".join(flags), retry=True, reference=first)
            revised = revised_record["reply"]
            if revised.strip():
                new_hard, new_judgment, new_flags = assess(revised)
                attempts.append({**revised_record, "review":new_judgment, "warnings":new_flags})
                # An invalid review can never clear a previous grounded concern.
                old_rank = (not judgment["valid"], len(flags))
                new_rank = (not new_judgment["valid"], len(new_flags))
                if not first.strip() or new_rank < old_rank:
                    first, hard, judgment, flags = revised, new_hard, new_judgment, new_flags
                    selected_record = revised_record
        except Exception as exc:
            retry_error = type(exc).__name__
    reviewed = judgment["valid"] and not judgment["issues"]
    if not judgment["valid"]:
        flags.append("تعذر التحقق من المراجعة الدلالية؛ الصياغة تحتاج مراجعة")
    if retry_error:
        flags.append("لم تكتمل محاولة إعادة الصياغة")
    if not first.strip():raise RuntimeError("المودل لم يولد ردًا")
    coach={k:v for k,v in plan.items() if v}
    return {
        "reply":first.strip(),"style_used":_style_display(style_key),"router_source":router_source,
        "reply_source":getattr(self,"reply_source","qwen_lora_generated"), "style_key":style_key if style_key in {"polite","firm","diplomatic","apology","clarify"} else (selected or "polite"),
        "generator":self.generator if hasattr(self, "generator") else "Qwen3.5-4B + Saudi LoRA",
        "coaching":coach,"review_status":"flagged" if flags else ("model_reviewed" if reviewed else "unverified"),
        "needs_review":bool(flags), "quality_warnings":list(dict.fromkeys(flags)),"was_retried":was_retried,
        "semantic_review":judgment, "generation_candidates":attempts, "retry_error":retry_error,
        "coaching_status":"model_generated" if coach else "unavailable", "coaching_error":coaching_error,
        "draft_before_register_normalization":selected_record["draft_before_register_normalization"],
        "register_normalization":selected_record["register_normalization"],
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
