"""Regression checks for register and preserving the reported customer intent."""
from LABEQ_V16_Coaching_Engine import local_warnings, reply_v16
from saudi_register import clean_writing, register_instruction, register_warnings


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

