"""Serving and provenance contracts; real model quality has a separate benchmark."""
import io
import json

import pytest
from ollama_inference import OllamaEngine
from generation_limits import GenerationBudgetError


class Router:
    model=object()
    faisal_ready=True

    def predict_style(self,*args):
        return "apology","faisal"


def install_provider(monkeypatch,capabilities=None):
    requests=[]
    def open_request(request,timeout):
        payload=json.loads(request.data);requests.append((request.full_url,payload))
        if request.full_url.endswith('/api/show'):
            result={"details":{"quantization_level":"Q4_K_M"},"capabilities":capabilities or ["completion"]}
        elif request.full_url.endswith('/api/generate'):
            result={"done":True,"done_reason":"load"}
        else:
            result={"message":{"content":"حقك علي، الغلط مني وأقدر وقتك."},"done_reason":"stop"}
        return io.BytesIO(json.dumps(result).encode())
    monkeypatch.setattr('ollama_inference.urlopen',open_request)
    return requests


def test_real_writer_does_not_claim_a_saudi_response_adapter(monkeypatch):
    calls=install_provider(monkeypatch)
    engine=OllamaEngine(Router(),'test-writer:14b')
    assert engine.reply_source=='ollama_generated'
    assert engine.predict_style('موقف','صديق','أعتذر')==('apology','faisal')
    assert engine.faisal_ready
    messages=[{'role':'user','content':'نسيت الموعد وأبي أعتذر'}]
    assert engine._one_generation(messages,max_tokens=256).startswith('حقك علي')
    assert calls[-1][1]['messages']==messages
    assert calls[-1][1]['options']['num_predict']==256
    assert calls[-1][1]['options']['repeat_penalty']==1.0


def test_embedding_model_cannot_be_used_as_a_writer(monkeypatch):
    install_provider(monkeypatch,['embedding'])
    with pytest.raises(ValueError,match='cannot generate'):
        OllamaEngine(Router(),'embedding-only')


def test_truncated_provider_text_is_not_returned_as_a_finished_reply(monkeypatch):
    install_provider(monkeypatch)
    engine=OllamaEngine(Router(),'writer')
    monkeypatch.setattr(engine,'_request',lambda *args:{'message':{'content':'نص غير مكتمل'},'done_reason':'length','eval_count':256})
    with pytest.raises(GenerationBudgetError) as error:
        engine._one_generation([{'role':'user','content':'موقف'}])
    assert error.value.partial_text=='نص غير مكتمل'


def test_invalid_policy_does_not_load_a_model(monkeypatch,tmp_path):
    calls=install_provider(monkeypatch)
    file=tmp_path/'policy.json';file.write_text(json.dumps({'system':'تعليمات','examples':[{'role':'assistant','content':'رد'}]}))
    with pytest.raises(ValueError):OllamaEngine(Router(),'writer',policy=file)
    assert all(not url.endswith('/api/generate') for url,_ in calls)


@pytest.mark.parametrize('url',['http://remote.example:11434','https://user:secret@remote.example','file:///tmp/model'])
def test_unprotected_remote_or_credential_bearing_urls_are_rejected(url):
    with pytest.raises(ValueError):OllamaEngine(Router(),'writer',base_url=url)
