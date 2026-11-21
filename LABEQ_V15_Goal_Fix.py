"""LABEQ V15: preserve user intent during Saudi LoRA inference.

Install in an already-running Colab after ``engine.load()``:

    from LABEQ_V15_Goal_Fix import install
    install(engine)

Or upload this Python file to the current Colab session and run:

    from google.colab import files
    uploaded = files.upload()
    exec(uploaded["LABEQ_V15_Goal_Fix.py"].decode("utf-8"))

This is a prompt/validation hotfix. It does NOT change LoRA weights or train Faisal.
"""
from __future__ import annotations

import contextvars
import re
from dataclasses import dataclass


_REPEATED = re.compile(r"(?:كل\s*(?:يوم|مر[ةه]|شوي|أسبوع|اسبوع|وقت)|يومي[ًاا]|دايم[ًاا]?|دائم[ًاا]?|باستمرار|بشكل\s*مستمر|متكرر[ةه]?|تتكرر|يتكرر|مرار[ًاا]|على\s*طول)")
_REPEAT_ACK = re.compile(r"(?:كل\s*(?:يوم|مر[ةه]|شوي|أسبوع|اسبوع|وقت)|دايم[ًاا]?|دائم[ًاا]?|باستمرار|مستمر|متكرر|مرة\s*و(?:را|بعد)\s*مرة|على\s*طول|كل\s*طلب|مو\s*كل\s*مرة)")
_REFUSAL = re.compile(r"(?:أرفض|ارفض|أقول\s*لا|ما\s*أقدر|لا\s*أقدر|مو\s*قادر|أوضح\s*حدود|أحط\s*حدود|حدودي|أعتذر\s*عن\s*الطلب|اعتذر\s*عن\s*الطلب|أخفف\s*الطلبات)")
_ONLY_TODAY = re.compile(r"(?:اليوم|هالمرة|هذي\s*المرة|حالي[ًاا]|الحين\s*ما|الوقت\s*الحالي)")
_FUTURE_PROMISE = re.compile(r"(?:نتفق\s*على\s*وقت|وقت\s*مناسب|وقت\s*ثاني|بعدين\s*أساعد|بكرة\s*أساعد|أساعد[كهاه]*\s*(?:بكرة|لاحق[ًاا]|بعدها)|لما\s*أفضى\s*أساعد)")
_UNSUPPORTED_SPECIFIC_APOLOGY = re.compile(r"(?:أعتذر\s*عن\s*(?:الصراخ|إهانتك|ضربك)|سامحني\s*إني\s*(?:صرخت|ضربتك))")

@dataclass(frozen=True)
class Brief:
    message: str
    goal: str
    relation: str
    repeated: bool
    recurring_refusal: bool
    work_conflict: bool


def brief_for(message: str, goal: str, relation: str = "") -> Brief:
    m, g = (message or "").strip(), (goal or "").strip()
    recurring = bool(_REPEATED.search(m))
    refusal = bool(_REFUSAL.search(g)) or bool(_REFUSAL.search(m))
    work_conflict = bool(re.search(r"(?:عندي\s*شغلي|عندي\s*مهامي|عندي\s*مسؤولياتي|شغلي\s*كثير|مشغول[ةه]?)", m))
    return Brief(m, g, relation or "", recurring, recurring and refusal, work_conflict)


def intent_guidance(brief: Brief) -> str:
    instructions = [
        "هذه ضوابط لمعنى الرد، وليست كلامًا ترسله للطرف الآخر:",
        f"الهدف الأصلي للمستخدم (احفظيه بالكامل): {brief.goal or 'رد يناسب الموقف'}.",
        "اكتبي للطرف الآخر بصيغة المتحدث، ولا تخترعي أحداثًا أو تفاصيل أو التزامات.",
        "لا تغيّري الهدف إلى اعتذار أو وعد أو رفض مؤقت ما لم يقصد المستخدم ذلك.",
        "استخدمي لهجة سعودية يومية طبيعية تناسب العلاقة، وابتعدي عن الفصحى المتكلفة.",
    ]
    if brief.recurring_refusal:
        instructions.extend([
            "المشكلة الأساسية في النص هي تكرار الطلبات، مو مجرد طلب اليوم.",
            "شرط نجاح الرد: وضّحي بلطف وبصراحة أن المساعدة لا يمكن أن تستمر كل يوم/كل مرة، مع الحفاظ على العلاقة.",
            "لا تكتفي بقول «اليوم ما أقدر» أو «هالمرة ما أقدر»؛ ولا تعرضي موعدًا بديلًا أو تعدي بالمساعدة لاحقًا من نفسك.",
        ])
        if brief.work_conflict:
            instructions.append("المستخدم ذكر انشغاله بمسؤولياته؛ اذكري هذا السبب الطبيعي بإيجاز بدون اختلاق أعذار.")
    elif brief.repeated:
        instructions.append("المستخدم وصف أمرًا متكررًا؛ حافظي على التكرار في الرسالة ولا تختصريه إلى واقعة لمرة واحدة.")
    if re.search(r"(?:أصلح|نصلح|ننهي\s*الخلاف|نتفاهم|سوء\s*فهم|تصالح)", brief.goal):
        instructions.append("للصلح: حافظي على التصرف اللي طلبه المستخدم في الموقف، مثل الاعتذار أو التوضيح أو المتابعة. لا تستبدليه بطلب حوار عام، ولا تنسبي له خطأ ما ذكره.")
    source = brief.message + " " + brief.goal
    if (
        re.search(r"تأخر|تأخير", source)
        and re.search(r"(?:إني|أني)\s+(?:بتابع|بأتابع)|أبي\s+أتابع", source)
        and re.search(r"موعد", source)
        and re.search(r"مو\s+متأكد|غير\s+مؤكد|بدون\s+ما\s+أعطي", source)
        and re.search(r"أعتذر|اعتذار", source)
    ):
        instructions.append("الرسالة لازم توصل هالثلاث نقاط اللي طلبها الشخص: اعتذار عن التأخير، وتأكيد متابعة الطلب، وتوضيح إنك ما تقدر تعطي موعد قبل ما تتأكد. لا تضيف وعد بوصوله بالوقت المناسب أو بأقرب وقت.")
    return "\n".join("- " + line for line in instructions)


def alignment_flags(reply: str, brief: Brief) -> list[str]:
    text = (reply or "").strip()
    flags: list[str] = []
    if brief.recurring_refusal:
        if not _REPEAT_ACK.search(text):
            flags.append("الرد تجاهل أن الطلب يتكرر وأن المطلوب حد مستمر، لا رفض اليوم فقط")
        if _FUTURE_PROMISE.search(text):
            flags.append("الرد وعد بتأجيل المساعدة بدل توضيح حدود المساعدة المتكررة")
        if _ONLY_TODAY.search(text) and not _REPEAT_ACK.search(text):
            flags.append("الرد حوّل رفض التكرار إلى رفض مؤقت")
    if _UNSUPPORTED_SPECIFIC_APOLOGY.search(text) and not re.search(r"(?:صراخ|صرخت|ضرب|إهانة|اهنت)", brief.message):
        flags.append("الرد افترض حدثًا أو خطأ لم يذكره المستخدم")
    return list(dict.fromkeys(flags))


_ACTIVE: contextvars.ContextVar[Brief | None] = contextvars.ContextVar("labeq_v15_intent", default=None)


def install(engine=None) -> None:
    """Idempotently attach the guard to the existing engine class and instance."""
    import labeq_engine as mod
    cls = mod.LabeqEngine
    if getattr(cls, "_labeq_v15_guard_installed", False):
        print("✅ LABEQ V15 Goal Guard مثبت مسبقًا؛ لم نكرّر التعديل")
        return

    old_reply = cls.reply
    old_generate = cls._one_generation
    old_quality = mod.quality_flags
    old_system = mod.SYSTEM_PROMPT

    mod.SYSTEM_PROMPT = old_system + "\n" + (
        "أولوية مطلقة: حلّي جوهر المشكلة التي ذكرها المستخدم، ولا تغيّري مدتها أو تكرارها أو هدفه. "
        "مثلًا رفض المساعدة كل يوم ليس رفضًا لليوم فقط. لا تعدي بوقت آخر دون طلب صريح. "
        "استهدفي غالبًا جملتين إلى ثلاث، بلهجة سعودية طبيعية وكلام قابل للإرسال."
    )

    def reply_with_intent(self, *args, **kwargs):
        message = args[0] if len(args) > 0 else kwargs.get("message", "")
        relation = args[1] if len(args) > 1 else kwargs.get("relation", "صديق")
        goal = args[2] if len(args) > 2 else kwargs.get("goal", "أبي رد مناسب")
        token = _ACTIVE.set(brief_for(message, goal, relation))
        try:
            result = old_reply(self, *args, **kwargs)
            if isinstance(result, dict) and result.get("reply_source") == "qwen_lora_generated":
                extra = alignment_flags(result.get("reply", ""), _ACTIVE.get())
                if extra:
                    result["quality_warnings"] = list(dict.fromkeys(list(result.get("quality_warnings") or []) + extra))
                    result["needs_review"] = True
            return result
        finally:
            _ACTIVE.reset(token)

    def generate_with_intent(self, messages, retry=False, use_adapter=True):
        context = _ACTIVE.get()
        if context and messages:
            new_messages = [dict(m) for m in messages]
            user_positions = [i for i, msg in enumerate(new_messages) if msg.get("role") == "user"]
            if user_positions:
                target_idx = user_positions[-1]
                guidance = intent_guidance(context)
                if retry:
                    previous = new_messages[-2].get("content", "") if len(new_messages) >= 2 else ""
                    flags = alignment_flags(previous, context)
                    if flags:
                        guidance += "\n- هذه أخطاء الصياغة السابقة التي يجب تصحيحها: " + "؛ ".join(flags)
                    guidance += "\n- أعيدي بناء الرد بناءً على تفاصيل الموقف، لا تبدلي كلمات الرد السابق فقط."
                new_messages[target_idx]["content"] = str(new_messages[target_idx].get("content", "")) + "\n\n" + guidance
            return old_generate(self, new_messages, retry=retry, use_adapter=use_adapter)
        return old_generate(self, messages, retry=retry, use_adapter=use_adapter)

    def quality_with_intent(reply, relation="", goal="", original=""):
        flags = list(old_quality(reply, relation, goal, original))
        context = _ACTIVE.get() or brief_for(original, goal, relation)
        return list(dict.fromkeys(flags + alignment_flags(reply, context)))

    cls.reply = reply_with_intent
    cls._one_generation = generate_with_intent
    cls._labeq_v15_guard_installed = True
    mod.quality_flags = quality_with_intent
    print("✅ LABEQ V15: تثبيت حفظ هدف المستخدم + اكتشاف الرفض المؤقت + إعادة صياغة موجهة")
    if engine is not None:
        print("Qwen loaded:", bool(getattr(engine, "model", None) is not None))
        print("Faisal loaded:", bool(getattr(engine, "faisal_ready", False)))
        print("ملاحظة: هذا إصلاح تعليمات وفحص جودة، وليس تدريبًا جديدًا؛ اختبري النتيجة الفعلية.")


# When executed via exec(uploaded[...].decode()), install into the current Colab session.
if __name__ == "__main__" or "engine" in globals():
    install(globals().get("engine"))
