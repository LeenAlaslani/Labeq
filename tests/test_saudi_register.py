"""Regression checks for register and preserving the reported customer intent."""
from LABEQ_V16_Coaching_Engine import local_warnings, reply_v16, semantic_review_issue
from saudi_register import clean_writing, normalize_saudi, register_instruction, register_warnings, writing_style


SCENARIO = (
    "عميل زعل لأن طلبه تأخر عن الموعد اللي وعدناه فيه، وأنا أبي أعتذر له "
    "وأوضح إني بتابع الموضوع بدون ما أعطيه موعد جديد مو متأكد منه."
)


def test_reported_formal_reply_cannot_pass_with_missing_followup():
    reply = "أعتذر عن التأخير، وما أردت أن أعطيكم موعدًا قبل ما يكون واضحًا."
    assert register_warnings(reply)
    assert any("متابعة" in flag for flag in local_warnings(reply, SCENARIO, "ننهي الخلاف", "diplomatic"))


def test_professional_saudi_is_allowed_without_forcing_slang():
    reply = "نعتذر لك عن تأخر طلبك. بأتابع الموضوع وأرجع لك بتحديث، وما أبي أعطيك موعد وأنا مو متأكد."
    assert not register_warnings(reply)
    assert not local_warnings(reply, SCENARIO, "ننهي الخلاف", "diplomatic")
    assert "سعودية مهنية" in register_instruction("عميل", "diplomatic")
    assert register_warnings("أود التأكد من الموعد.", "اجعلي الصياغة رسمية ومهنية")


def test_explicit_fusha_request_and_other_dialects():
    assert not register_warnings("أود التأكد من الموعد.", "اكتبي بالفصحى")
    assert register_warnings("أنا مش متأكدش من الموعد")
    assert not register_warnings("ما أقدر أعطيك موعد وأنا مو متأكد")


def test_default_writing_removes_vowels_without_changing_letters():
    assert clean_writing("أُتابعُ الطَّلبَ غدًا") == "أتابع الطلب غدا"
    assert clean_writing("أُتابعُ", "اكتبي بالتشكيل") == "أُتابعُ"


def test_surface_edit_preserves_negation_tense_numbers_and_quoted_text():
    text = 'ما أردت أن أغير موعد 12 مايو. لا أستطيع تأكيده. سأخبرك. قال «أود أن أتأكد».'
    edited, changes = normalize_saudi(text)
    assert edited == 'ما كنت أبي أغير موعد 12 مايو. ما أقدر أؤكده. بعطيك خبر. قال «أود أن أتأكد».'
    assert changes
    assert normalize_saudi(text, "اكتبي بالفصحى")[0] == text
    assert normalize_saudi("لا أريد موعدا جديدا")[0] == "ما أبي موعدا جديدا"
    assert normalize_saudi("لا أستطيع المساعدة")[0] == "لا أستطيع المساعدة"
    assert normalize_saudi("لن أستطيع أساعدك")[0] == "ما بأقدر أساعدك"


def test_present_followup_is_changed_to_future_only_when_requested():
    assert normalize_saudi("أعتذر وأتابع الطلب")[0] == "أعتذر وأتابع الطلب"
    assert normalize_saudi("أعتذر وأتابع الطلب وأخبرك", context=SCENARIO)[0] == "أعتذر وبأتابع الطلب وأعطيك خبر"


def test_writing_labels_match_training_without_changing_communication_style():
    assert writing_style("diplomatic") == "عفوي"
    assert writing_style("clarify") == "واضح"
    assert writing_style("apology", "اجعلي الصياغة رسمية ومهنية") == "مهني"


def test_clear_collocation_repairs_do_not_change_burden_or_quoted_speech():
    text = "ما قصدت إني أقلل عليك، بس أبي أسألك."
    assert normalize_saudi(text, context="فهمت سؤالي على إنه تقليل منها")[0] == "ما قصدت إني أقلل منك، بس أبي أسألك."
    burden = "ما قصدت إني أقلل عليك الشغل."
    assert normalize_saudi(burden, context="تقليل من شغلها")[0] == burden
    assert normalize_saudi("ممكن أوضح لي المطلوب؟")[0] == "ممكن توضيح المطلوب؟"
    assert normalize_saudi("ممكن أوضح لك المطلوب؟")[0] == "ممكن أوضح لك المطلوب؟"
    assert normalize_saudi('قال «ممكن أوضح لي المطلوب؟»')[0] == 'قال «ممكن أوضح لي المطلوب؟»'


def test_model_approval_does_not_override_register_and_followup_checks():
    class Engine:
        generator = "test fixture"

        def load(self):
            return self

        def predict_style(self, *args):
            return "diplomatic", "faisal"

        def _one_generation(self, messages, retry=False, use_adapter=True):
            if not use_adapter:
                if "أربع سطور" in messages[-1]["content"]:
                    return "الخطوة: لا تعتذر للعميل واطلب منه الاتصال بمدير آخر"
                return "النتيجة: مناسب"
            # A mistaken generated plan must not become a generation instruction.
            assert "اطلب منه الاتصال بمدير آخر" not in messages[-1]["content"]
            return (
                "نعتذر لك عن تأخر طلبك. بأتابع الموضوع، وما أبي أعطيك موعد وأنا مو متأكد."
                if retry else "أعتذر عن التأخير، وما أردت أن أعطيكم موعدا قبل ما يكون واضحا."
            )

    result = reply_v16(Engine(), SCENARIO, "عميل", "ننهي الخلاف")
    assert result["was_retried"] and not result["needs_review"]
    assert result["router_source"] == "faisal"
    assert result["reply_source"] == "qwen_lora_generated"
    assert "بأتابع" in result["reply"]


def test_advisory_style_opinion_does_not_rewrite_a_grounded_saudi_reply():
    class Engine:
        drafts = 0

        def load(self):
            return self

        def predict_style(self, *args):
            return "diplomatic", "faisal"

        def _one_generation(self, messages, retry=False, use_adapter=True):
            if use_adapter:
                self.drafts += 1
                return "نعتذر لك عن التأخير. بأتابع الموضوع، وما أبي أعطيك موعد وأنا مو متأكد."
            return "النتيجة: غير مناسب\nالسبب: استخدام كلمة بس يضعف النبرة"

    engine = Engine()
    result = reply_v16(engine, SCENARIO, "عميل", "ننهي الخلاف")
    assert engine.drafts == 1 and not result["was_retried"]
    assert result["needs_review"]  # Keep the model's fallible opinion visible.


def test_apology_instruction_is_not_an_apology_message():
    assert local_warnings("اعتذري عن نسيان الموعد", "نسيت موعد صديقتي", "أعتذر عن غلطتي", "apology")


def test_reflexive_clarification_error_is_flagged_but_a_direct_question_is_allowed():
    assert local_warnings("ما حددت لي نسخة أو وقت تسليم، ممكن أوضح لي المطلوب؟", "المشرفة طلبت ملف", "أطلب توضيح", "clarify")
    assert not local_warnings("ممكن توضحين لي أي نسخة مطلوبة ومتى موعد التسليم؟", "المشرفة طلبت ملف", "أطلب توضيح", "clarify")


def test_advisory_opinion_does_not_veto_a_concrete_intent_repair():
    class Engine:
        def load(self):
            return self

        def _one_generation(self, messages, retry=False, use_adapter=True):
            if use_adapter:
                return "حقك علي، نسيت الموعد وخليتك تنتظرين." if retry else "اعتذري عن نسيان الموعد."
            return "النتيجة: غير مناسب\nالسبب: العبارة قصيرة"

    result = reply_v16(Engine(), "نسيت موعد صديقتي", "صديق", "أعتذر عن غلطتي", "اعتذار")
    assert result["reply"].startswith("حقك علي")
    assert result["was_retried"] and result["needs_review"]


def test_specific_deadline_concern_triggers_repair_without_demanding_a_new_date():
    assert semantic_review_issue("وعود بالوقت المناسب مما يتعارض مع عدم إعطاء موعد")
    assert not semantic_review_issue("الرسالة تفتقر إلى تحديد موعد جديد")

    class Engine:
        def load(self):
            return self

        def predict_style(self, *args):
            return "diplomatic", "faisal"

        def _one_generation(self, messages, retry=False, use_adapter=True):
            if use_adapter:
                return (
                    "نعتذر لك عن التأخير. بأتابع الطلب، وما أبي أعطيك موعد وأنا مو متأكد."
                    if retry else "نعتذر لك عن التأخير. بأتابع الطلب عشان نوصله لك بالوقت المناسب."
                )
            if "بالوقت المناسب" in messages[-1]["content"]:
                return "النتيجة: غير مناسب\nالسبب: وعود بالوقت المناسب مما يتعارض مع عدم إعطاء موعد"
            return "النتيجة: مناسب"

    result = reply_v16(Engine(), SCENARIO, "عميل", "ننهي الخلاف")
    assert result["was_retried"]
    assert "مو متأكد" in result["reply"] and not result["needs_review"]

