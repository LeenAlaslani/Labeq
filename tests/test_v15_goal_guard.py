"""Offline semantic regression tests: no GPU or model weights required."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import LABEQ_V15_Goal_Fix as guard
import labeq_engine

CASE = 'زميلتي تطلب مني أساعدها في شغلها كل يوم، وأنا عندي شغلي وما أبي أزعلها، بس ما أقدر أساعد كل مرة.'
GOAL = 'أرفض الطلب بأسلوب محترم'

class TestGoalGuard(unittest.TestCase):
    def test_repeated_help_is_not_temporary(self):
        brief = guard.brief_for(CASE, GOAL, 'عمل')
        self.assertTrue(brief.recurring_refusal)
        bad = 'أقدر طلبك بس اليوم ما أقدر أساعدك، نتفق على وقت مناسب.'
        self.assertGreaterEqual(len(guard.alignment_flags(bad, brief)), 2)
        good = 'أحب أساعدك، بس صعب علي أساعدك كل يوم وأنا عندي شغلي. أتمنى تتفهمين إني ما أقدر كل مرة.'
        self.assertEqual(guard.alignment_flags(good, brief), [])

    def test_does_not_invent_recurring_without_evidence(self):
        brief = guard.brief_for('زميلتي طلبت مني مساعدة اليوم وأنا مشغولة', GOAL, 'عمل')
        self.assertFalse(brief.recurring_refusal)
        self.assertEqual(guard.alignment_flags('والله ودي أساعدك بس اليوم ما أقدر.', brief), [])

    def test_existing_model_workflow_router_and_lora_retained(self):
        cls=labeq_engine.LabeqEngine
        old_load,old_predict,old_gen=cls.load,cls.predict_style,cls._one_generation
        calls=[]
        def stub_load(self):return self
        def stub_predict(self,msg,relation,goal):return 'polite','faisal'
        def stub_gen(self,messages,retry=False,use_adapter=True):
            calls.append((messages,retry,use_adapter))
            if not retry:return 'أقدر طلبك بس اليوم ما أقدر أساعدك، نتفق على وقت مناسب.'
            return 'أحب أساعدك، بس صعب علي أساعدك كل يوم وأنا عندي شغلي. أتمنى تتفهمين إني ما أقدر كل مرة.'
        try:
            cls.load,cls.predict_style,cls._one_generation=stub_load,stub_predict,stub_gen
            guard.install()
            fake=object.__new__(cls)
            result=fake.reply(CASE,'عمل',GOAL,'تلقائي',generation_mode='مولّد فقط')
            self.assertEqual(result['router_source'],'faisal')
            self.assertEqual(result['reply_source'],'qwen_lora_generated')
            self.assertTrue(result['was_retried'])
            self.assertIn('كل مرة',result['reply'])
            self.assertFalse(result['needs_review'])
            self.assertEqual(len(calls),2)
            self.assertIn('تكرار الطلبات',calls[0][0][-1]['content'])
            self.assertIn('هذه أخطاء الصياغة',calls[1][0][-1]['content'])
        finally:
            # Isolate other tests from patched class in same interpreter.
            cls.load=old_load
            cls.predict_style=old_predict
            cls._one_generation=old_gen

if __name__=='__main__': unittest.main()
