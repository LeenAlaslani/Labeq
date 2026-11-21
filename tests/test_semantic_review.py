"""Schema/grounding and repair control flow, not model-quality measurements."""
import json
import pytest
from LABEQ_V16_Coaching_Engine import reply_v16
from semantic_review import parse_review

MESSAGE="أبي أعتذر عن الغلط بدون ما أبرر لنفسي وأوضح لها إنها مهمة عندي"
GOAL="أعتذر وأصلح الموقف"


def review(status="met", reason="", quote="بدون ما أبرر لنفسي"):
    return json.dumps({"checks":[{"source_quote":quote,"status":status,"reason":reason}],"unsupported":[]},ensure_ascii=False)


@pytest.mark.parametrize("text",[
    "النتيجة: مناسب", '{"checks":[]}', '{"checks":[',
    review(quote="يجب تحديد موعد للتعويض"), review(status="pass"), review(status="missing"),
])
def test_uncertain_or_unanchored_reviews_never_pass(text):
    assert not parse_review(text,MESSAGE,GOAL,"حقك علي")["valid"]


def test_grounded_failure_does_not_depend_on_reason_keywords():
    result=parse_review(review("contradicted","الرسالة تبرر الخطأ بدل أن تعترف بالذنب فقط"),MESSAGE,GOAL,"كنت مشغول")
    assert result["valid"] and result["issues"]


def test_reviewer_cannot_add_nonexistent_claims():
    obj=json.loads(review());obj["unsupported"]=["بكرة أعوضك"]
    assert not parse_review(json.dumps(obj),MESSAGE,GOAL,"حقك علي")["valid"]


def test_grounded_failure_triggers_repair_and_keeps_provenance():
    class Engine:
        def load(self):pass
        def _one_generation(self,messages,retry=False,use_adapter=True,max_tokens=256):
            if use_adapter:return "حقك علي، أنت مهمة عندي والغلط مني." if retry else "كنت مشغول، أرجو تفهميني."
            if "أربع سطور" in messages[-1]["content"]:return "جوهر الموقف: اعتذار"
            return review() if "الرسالة: حقك علي" in messages[-1]["content"] else review("contradicted","الرسالة تبرر الخطأ بدل أن تعترف بالذنب فقط")
    result=reply_v16(Engine(),MESSAGE,"صديق",GOAL,"اعتذار")
    assert result["was_retried"] and not result["needs_review"]
    assert len(result["generation_candidates"])==2
    assert result["semantic_review"]["valid"]
    assert result["reply"].startswith("حقك علي")


def test_invalid_second_review_cannot_clear_a_known_failure():
    class Engine:
        def load(self):pass
        def _one_generation(self,messages,retry=False,use_adapter=True,max_tokens=256):
            if use_adapter:return "حقك علي، أنت مهمة عندي والغلط مني." if retry else "كنت مشغول، أرجو تفهميني."
            if "أربع سطور" in messages[-1]["content"]:return ""
            return "النتيجة: مناسب" if "الرسالة: حقك علي" in messages[-1]["content"] else review("contradicted","تبرير")
    result=reply_v16(Engine(),MESSAGE,"صديق",GOAL,"اعتذار")
    assert result["needs_review"] and result["reply"].startswith("كنت مشغول")


def test_unparseable_review_is_visible_and_unverified():
    class Engine:
        def load(self):pass
        def _one_generation(self,*args,**kwargs):return "آسف على الغلط، أنت مهمة عندي."
    result=reply_v16(Engine(),MESSAGE,"صديق",GOAL,"اعتذار")
    assert result["needs_review"] and result["review_status"]!="model_reviewed"
