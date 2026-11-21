"""Selection rejection, deadline and selected-attempt provenance guards."""
from types import SimpleNamespace
import sys
import time
import random

import pytest

from cloud.ensemble_engine import EnsembleEngine
from cloud.semantic_teacher import SemanticTeacher
from generation_limits import GenerationBudgetError


def fixture_engine(choice):
    engine=EnsembleEngine.__new__(EnsembleEngine)
    engine.deadline=time.monotonic()+120
    engine.current_case={'message':'موقف للاختبار فقط','relation':'عمل','goal':'هدف للاختبار'}
    engine.automatic_plan={'facts':[],'acts':['stated action'],'avoid':[]}
    engine.rng=random.Random(20261122);engine.attempt_trace=[];engine.last_writer_provenance={}
    engine.adapter_revision='pilot-revision';engine.v2_revision='v2-revision'
    engine.candidate_adapter_shas={'pilot':'pilot-hash','v2':'v2-hash'}
    engine.adapter_labels={'pilot':'pilot fixture','v2':'v2 fixture'}
    engine.policies={key:('fixture policy',[]) for key in ['clean','fewshot']}
    engine.policy_shas={'clean':'clean-hash','fewshot':'fewshot-hash'}
    writer=SimpleNamespace(last_generation={'finish_reason':'stop'})
    writer._one_generation=lambda *a,**k:'Actual fixture generation '+writer.active_writer_adapter
    engine.writer=writer;engine.teacher=SimpleNamespace(select=lambda *a:choice)
    return engine


def test_reject_all_never_becomes_a_closest_candidate_fallback():
    engine=fixture_engine('E')
    with pytest.raises(RuntimeError,match='rejected all'):
        engine._one_generation([{'role':'user','content':'original source'}])
    assert engine.last_writer_provenance=={}


def test_selected_provenance_matches_the_actual_selected_model():
    engine=fixture_engine('A')
    text=engine._one_generation([{'role':'user','content':'original source'}])
    record=engine.attempt_trace[0];name=record['anonymous_key']['A']
    selected=record['candidates'][name]
    assert text==selected['reply']
    assert engine.last_writer_provenance['adapter_sha256']==selected['adapter_sha256']
    assert len(record['candidates'])==4


def test_semantic_custom_time_stop_cannot_certify_a_complete_reply(monkeypatch):
    import cloud.semantic_teacher as module
    clock={'now':0}
    monkeypatch.setattr(module,'time',SimpleNamespace(monotonic=lambda:clock['now']))
    monkeypatch.setitem(sys.modules,'llama_cpp',SimpleNamespace(StoppingCriteriaList=lambda items:items,LlamaGrammar=None))
    teacher=SemanticTeacher();teacher.tokenizer=SimpleNamespace(apply_chat_template=lambda *a,**k:'prompt')
    def completion(**kwargs):
        clock['now']=2
        assert kwargs['stopping_criteria'][0]([],[]) is True
        return {'choices':[{'text':'نص توقف قبل اكتماله','finish_reason':'stop'}],'usage':{}}
    teacher.model=SimpleNamespace(create_completion=completion)
    with pytest.raises(GenerationBudgetError):teacher.generate([],256,1,'writer')
    assert teacher.trace[0]['timed_out'] is True


def test_expired_semantic_budget_does_not_start_inference():
    teacher=SemanticTeacher()
    with pytest.raises(TimeoutError):teacher.generate([],256,time.monotonic()-1,'writer')


def test_private_diagnostic_failure_never_claims_a_generated_reply(monkeypatch):
    engine=fixture_engine('E');engine.lock=__import__('threading').RLock();engine.load=lambda:engine
    def invalid_plan(*args):raise ValueError('Invalid JSON')
    engine.teacher.plan=invalid_plan;engine.teacher.trace=[]
    monkeypatch.setenv('LABEQ_RETURN_GENERATION_TRACE','1')
    result=engine.reply('موقف للاختبار فقط')
    assert result['status']=='generation_failed'
    assert 'reply' not in result and 'reply_source' not in result
    assert result['actual_router_result'] is None


def test_queue_dispatch_enters_the_explicit_backend_context_wrapper():
    from cloud.space_app import execute_reply
    observed=[]
    engine=SimpleNamespace(configured_reply=lambda *args:observed.append(args) or {'prepared':True})
    request=SimpleNamespace(message='الموقف الأصلي',relation='صديق',goal='الهدف الأصلي',style='تلقائي',
        speaker_gender='غير محدد',recipient_gender='غير محدد',history=[],generation_mode='مولّد فقط')
    assert execute_reply(engine,request)=={'prepared':True}
    assert observed[0][:3]==('الموقف الأصلي','صديق','الهدف الأصلي')
