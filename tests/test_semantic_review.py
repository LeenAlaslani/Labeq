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


def test_advisory_failure_preserves_the_actual_generated_reply():
    class Engine:
        def load(self):pass
        def _one_generation(self,messages,use_adapter=True,**kwargs):
            if not use_adapter:raise TimeoutError('review unavailable')
            return 'حقك علي، الغلط مني وأنت مهمة عندي.'
    result=reply_v16(Engine(),MESSAGE,'صديق',GOAL,'اعتذار')
    assert result['reply'].startswith('حقك علي')
    assert result['coaching_status']=='unavailable'
    assert result['review_status']!='model_reviewed' and result['needs_review']


def test_identical_normalized_retries_preserve_the_selected_raw_draft():
    class Engine:
        def load(self):pass
        def _one_generation(self,messages,retry=False,use_adapter=True,**kwargs):
            if use_adapter:
                return 'ما أبي أبرر لنفسي، أنت مهمة عندي.' if retry else 'لا أريد أبرر لنفسي، أنت مهمة عندي.'
            if 'أربع سطور' in messages[-1]['content']:return ''
            return review('missing','لم يعتذر عن الخطأ')
    result=reply_v16(Engine(),MESSAGE,'صديق',GOAL,'اعتذار')
    attempts=result['generation_candidates']
    assert result['was_retried'] and len(attempts)==2
    assert attempts[0]['reply']==attempts[1]['reply']
    assert result['draft_before_register_normalization'].startswith('لا أريد')
    assert attempts[1]['draft_before_register_normalization'].startswith('ما أبي')
    assert result['register_normalization']==attempts[0]['register_normalization']


def test_rejected_retry_cannot_relabel_the_first_selected_adapter():
    class Engine:
        def load(self):pass
        def _one_generation(self,messages,retry=False,use_adapter=True,**kwargs):
            if use_adapter:
                self.last_writer_provenance={'generator':'second-model' if retry else 'first-model'}
                return 'حقك علي، أنت مهمة عندي.' if retry else 'كنت مشغول، أرجو تفهميني.'
            if 'أربع سطور' in messages[-1]['content']:return ''
            return review('missing','لم يعتذر عن الخطأ')
    result=reply_v16(Engine(),MESSAGE,'صديق',GOAL,'اعتذار')
    assert result['was_retried']
    assert result['generator']=='first-model'
    assert result['writer_provenance']['generator']=='first-model'
