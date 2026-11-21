"""CPU-only checks. These don't test real model quality or Colab serving."""
import unittest,sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import LABEQ_V16_Coaching_Engine as v16
import labeq_engine as base
from model_bridge import request_payload

def approval(prompt):
    quote=prompt.split("الموقف: ",1)[1].split("\nالعلاقة:",1)[0]
    return json.dumps({"checks":[{"source_quote":quote,"status":"met","reason":""}],"unsupported":[]},ensure_ascii=False)

class Tests(unittest.TestCase):
    def test_plan_parsing_and_no_fabrication(self):
        p=v16.parse_plan('جوهر الموقف: اختلاف في جدول العمل\nالهدف: طلب مساعدة\nالخطوة: اقترحي حوارًا\nانتبهي: لا تفترضي وجود اتفاق سابق')
        self.assertEqual(p['core'],'اختلاف في جدول العمل')
        self.assertIn('حوار',p['strategy'])
        self.assertFalse(v16.parse_plan('not a structured plan')['risk'])

    def test_request_instruction_not_mixed_into_fact(self):
        x=request_payload('زميلتي تطلب مني أساعدها','work','أوضح حدودي',style_key='apology',
            instruction='غيّري الأسلوب إلى اعتذار مهذب',history=[{'role':'assistant','content':'أحب أساعدك'}])
        self.assertEqual(x['message'],'زميلتي تطلب مني أساعدها')
        self.assertEqual(x['goal'],'أوضح حدودي')
        self.assertEqual(x['history'][-1]['role'],'user')
        self.assertIn('تعليمات تعديل الرد',x['history'][-1]['content'])
        self.assertEqual(x['style'],'اعتذار')

    def test_model_router_style_and_contextual_reply(self):
        cls=base.LabeqEngine
        orig=(cls.load,cls.predict_style,cls._one_generation,cls.reply)
        calls=[]
        def load(self):return self
        def predict(self,m,r,g):return 'polite','faisal'
        def generate(self,messages,retry=False,use_adapter=True,max_tokens=256):
            prompt=messages[-1]['content'];calls.append((prompt,use_adapter))
            if not use_adapter and 'أربع سطور' in prompt:
                return 'جوهر الموقف: المساعدة اليومية تضغط على وقتها\nالهدف: توضيح حدود المساعدة\nالخطوة: ابدئي بتقدير الصداقة ثم ارفضي التكرار\nانتبهي: لا توعدين بوقت آخر'
            if not use_adapter and 'source_quote' in prompt:
                return approval(prompt)
            if 'طريقة التواصل: اعتذار' in prompt:
                return 'آسفة إني ما أقدر أساعدك كل يوم، عندي شغلي وأحتاج أركز عليه. أتمنى تتفهمين.'
            return 'أحب أساعدك، بس صعب علي أساعدك كل يوم وأنا عندي شغلي. أتمنى تتفهمين إني ما أقدر كل مرة.'
        try:
            cls.load=load;cls.predict_style=predict;cls._one_generation=generate
            v16.install()
            fake=object.__new__(cls)
            a=fake.reply('زميلتي تطلب مني أساعدها كل يوم، وأنا عندي شغلي','عمل','أوضح حدودي','تلقائي',generation_mode='مولّد فقط')
            b=fake.reply('زميلتي تطلب مني أساعدها كل يوم، وأنا عندي شغلي','عمل','أوضح حدودي','اعتذار',generation_mode='مولّد فقط')
            self.assertNotEqual(a['reply'],b['reply'])
            self.assertEqual(a['router_source'],'faisal')
            self.assertEqual(b['router_source'],'user_selected')
            self.assertEqual(b['style_key'],'apology')
            self.assertIn('المساعدة',a['coaching']['core'])
            self.assertFalse(a['needs_review']);self.assertFalse(b['needs_review'])
            self.assertEqual(sum(x[1] is False for x in calls),4)
            self.assertEqual(sum(x[1] is True for x in calls),2)
            self.assertNotIn('اعتذري عن تصرف خاطئ إذا ذكره المستخدم',a['reply'])
        finally:
            cls.load,cls.predict_style,cls._one_generation,cls.reply=orig
            if hasattr(cls,'_labeq_v16_installed'):del cls._labeq_v16_installed

    def test_no_guarantee_from_unparseable_reviewer(self):
        self.assertEqual(v16._parse_review('no structured verdict')[0],None)
        self.assertEqual(v16._parse_review('النتيجة: غير مناسب\nالسبب: غيّر الهدف')[0],False)
        self.assertEqual(v16._parse_review('النتيجة: مناسب\nالسبب: عالج الهدف')[0],True)

if __name__=='__main__':unittest.main()


def test_flagged_candidate_is_reviewed_again_after_retry():
    class Engine:
        def load(self):
            pass

        def _one_generation(self, messages, retry=False, use_adapter=True, max_tokens=256):
            if use_adapter:
                return (
                    "أحب أساعدك، بس ما أقدر أساعد كل يوم وأنا عندي شغلي."
                    if retry else "أعتذر ما أقدر أساعدك اليوم، ممكن أساعدك بكرة."
                )
            prompt = messages[-1]["content"]
            if "أربع سطور" in prompt:
                return "جوهر الموقف: تتكرر طلبات المساعدة"
            return approval(prompt) if "الرسالة: أحب" in prompt else json.dumps({"checks":[{"source_quote":"كل يوم","status":"contradicted","reason":"حول الحد إلى تأجيل"}],"unsupported":[]},ensure_ascii=False)

    output = v16.reply_v16(Engine(), "زميلتي تطلب المساعدة كل يوم وأنا عندي شغلي", "عمل", "أوضح حدودي", "حازم")
    assert output["was_retried"]
    assert output["review_status"] == "model_reviewed"
    assert not output["needs_review"]
    assert "كل يوم" in output["reply"]


def test_original_faisal_task_structure():
    task = base.make_faisal_task("خلاف مع صديقة", "صديقة", "أبي نتصالح")
    assert task["state"] == {"الموقف": "خلاف مع صديقة", "العلاقة": "صديقة", "الهدف": "أبي نتصالح"}
    assert [option["label"] for option in task["options"]] == list("ABCDEF")
    assert task["options"][-1]["key"] == "insufficient"
