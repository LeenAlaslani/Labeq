"""Saudi writing guidance and narrow diagnostics; no canned scenario replies."""
import re


_VOWELS = re.compile(r"[\u064b-\u0652\u0670]")
_FUSHA_REQUEST = re.compile(r"(?:بالفصحى|بالعربية الفصحى|لغة عربية فصحى)")
_STIFF = re.compile(
    r"(?:\b(?:أود|أرغب|إنني|يرجى|يتسنى|نحيطكم)\b|"
    r"أردت أن|سوف (?:أقوم|نقوم)|علما بأن|حرصا على|لن أتمكن|لا أستطيع)"
)
_OTHER_DIALECT = re.compile(r"(?:عايز[ةه]?|دلوقتي|متأكدش|مفيش|مافيش|إزاي|ازاي|أوي|حضرتك|\bمش\b)")

SAUDI_SYSTEM = """أنت لبق، مساعد سعودي يكتب الرسالة اللي الشخص بيرسلها للطرف الثاني.
اكتب بنفس اللهجة السعودية اليومية اللي بالموقف، بكلام طبيعي وقصير وواضح.
مع العميل والمدير خلك محترم ومهني بنفس لهجتنا، ومع الأهل والأصدقاء خلك قريب من كلام الواتساب.
من كلامنا: ودي، ما أقدر، مو متأكد، بأتابع، أعطيك خبر. استخدم اللي يناسب المعنى.
احفظ الموقف والطلب كامل بكل قيوده، وخلي الاعتذار أو التوضيح أو الحد المطلوب واضح.
اكتب الرسالة فقط بدون تشكيل أو تنوين أو شرح. اعتمد على حقائق الشخص، بدون أعذار أو مواعيد أو التزامات من عندك."""

# Different situations demonstrate register. These are prompt examples, never UI results.
SAUDI_EXAMPLES = ()


def explicit_fusha(modifier):
    return bool(_FUSHA_REQUEST.search(modifier or ""))


def clean_writing(text, modifier=""):
    if re.search(r"(?:بالتشكيل|مع التشكيل)", modifier or ""):
        return text.strip()
    return _VOWELS.sub("", text).strip()


def register_instruction(relation, style, modifier=""):
    if explicit_fusha(modifier):
        return "المستخدم طلب الفصحى صراحة؛ استخدم عربية واضحة وبسيطة مع حفظ المعنى."
    if relation in {"عميل", "عمل", "جامعة"} or style == "formal" or "رسمية" in modifier:
        return "اكتب بسعودية مهنية محترمة مثل رسالة واتساب للعمل: واضحة وطبيعية، مو خطاب فصيح ولا مزاح وألقاب مبالغ فيها."
    return "اكتب بسعودية يومية مثل ما تكلم شخص قريب منك، بدون فصحى متكلفة ولا مبالغة بالعامية."


def writing_style(style, modifier=""):
    # Faisal's social action and the LoRA's trained writing labels are distinct.
    if explicit_fusha(modifier):
        return "رسمي"
    if style == "formal" or "رسمية" in modifier:
        return "مهني"
    return "واضح" if style in {"firm", "clarify"} else "عفوي"


# Narrow phrase edits preserve negation, tense and factual content. They never
# add a greeting, apology, excuse, date, promise, or a complete scenario reply.
_PHRASES = (
    ("لم أخبرك", "ما عطيتك خبر"), ("لن أخبرك", "ما بأعطيك خبر"),
    ("لن أستطيع الحضور", "ما بأقدر أحضر"), ("لا أستطيع الحضور", "ما أقدر أحضر"),
    ("لا أستطيع تأكيده", "ما أقدر أؤكده"),
    ("لا أستطيع إعطاء", "ما أقدر أعطي"),
    ("لا أريد", "ما أبي"), ("أردت أن", "كنت أبي"),
    ("أود أن", "ودي"), ("أحتاج إلى أن", "أحتاج"),
    ("أحتاج إلى", "أحتاج"), ("سوف أتابع", "بأتابع"),
    ("سوف أراجع", "بأراجع"), ("سأتابع", "بأتابع"),
    ("سأراجع", "بأراجع"), ("سأخبرك", "بعطيك خبر"),
    ("سأبلغك", "بعطيك خبر"), ("أخبرك", "أعطيك خبر"),
    ("غير متأكد", "مو متأكد"), ("لست متأكدا", "مو متأكد"),
    ("لأنني", "لأني"), ("إنني", "إني"),
    ("حاليا", "الحين"), ("أريد", "أبي"), ("أود", "ودي"),
    ("الذي", "اللي"), ("التي", "اللي"),
    ("قبل أن", "قبل ما"), ("حتى أتأكد", "لين أتأكد"),
    ("حتى نتأكد", "لين نتأكد"), ("حتى يتضح", "لين يتضح"),
    ("ممكن أوضح لي", "ممكن توضيح"), ("ممكن أشرح لي", "ممكن شرح"),
)


def normalize_saudi(text, modifier="", context=""):
    if explicit_fusha(modifier):
        return text, []
    edits = []
    # Keep quotations intact rather than changing somebody else's quoted words.
    parts = re.split(r'("[^"\n]*"|«[^»]*»)', text)
    for index in range(0, len(parts), 2):
        segment = parts[index]
        for original, replacement in _PHRASES:
            segment, count = re.subn(
                r"(?<!\w)([وف]?)" + re.escape(original) + r"(?!\w)",
                lambda match: match.group(1) + replacement, segment,
            )
            if count:
                edits.append(original + " → " + replacement)
        modal = r"(?<!\w)([وف]?)(لا|لن) أستطيع (?=أ(?:ساعد|عطي|حدد|ؤكد|تأكد|لتزم|حضر|خلص|رد|رسل|سلم|شارك|واصل|جي|تحمل|غير|تابع))"
        segment, count = re.subn(
            modal,
            lambda match: match.group(1) + ("ما بأقدر " if match.group(2) == "لن" else "ما أقدر "),
            segment,
        )
        if count:
            edits.append("negated ability before a first-person verb → ما أقدر / ما بأقدر")
        if re.search(r"(?:إني|أني)\s+(?:بتابع|بأتابع)|أبي\s+أتابع", context):
            segment, count = re.subn(r"(?<!\w)وأتابع(?!\w)", "وبأتابع", segment)
            if count:
                edits.append("وأتابع → وبأتابع (requested follow-up)")
        if re.search(r"(?:تقليل|أقلل)\s+من(?:ك|ه|ها|كم|هن)(?:\W|$)", context):
            segment, count = re.subn(
                r"(?<!\w)(ما (?:قصدت|قصدي)(?: إني)? )أقلل عليك(?=[،.!؟]|$)",
                r"\1أقلل منك", segment,
            )
            if count:
                edits.append("أقلل عليك → أقلل منك (explicit disrespect context)")
        parts[index] = segment
    return "".join(parts), list(dict.fromkeys(edits))


def register_warnings(text, modifier=""):
    plain = _VOWELS.sub("", text)
    flags = []
    if _OTHER_DIALECT.search(plain):
        flags.append("الصياغة فيها تعبير من لهجة غير سعودية")
    if not explicit_fusha(modifier) and _STIFF.search(plain):
        flags.append("الصياغة فصيحة أو إدارية متكلفة؛ أعدها بسعودية طبيعية مع حفظ المعنى")
    return flags
