import base64
import io
import json
import wave

import httpx
import pytest
from fastapi.testclient import TestClient

import app as web
import labeq_api


SCENARIO = {"message": "صديقتي تطلب مساعدتي كل يوم وأنا عندي شغلي", "relation": "friend", "goal": "أوضح حدودي"}
GENERATED = {
    "reply": "ودي أساعدك، بس ما أقدر كل يوم وأنا عندي شغلي.",
    "style_key": "firm",
    "router_source": "faisal",
    "reply_source": "qwen_lora_generated",
    "coaching": {"core": "تتكرر طلبات المساعدة اليومية"},
}


@pytest.fixture
def web_client(monkeypatch):
    monkeypatch.setattr(web, "MODEL_MODE", "real")
    monkeypatch.setenv("LABEQ_MODEL_API_URL", "https://inference.example")
    monkeypatch.setenv("LABEQ_MODEL_API_KEY", "test-model-key")
    return TestClient(web.app)


@pytest.fixture
def upstream(monkeypatch):
    monkeypatch.setattr(web.app.state, "voice_retry_after", 0, raising=False)
    client_class = httpx.AsyncClient

    def install(handler):
        monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: client_class(
            transport=httpx.MockTransport(handler), **kw,
        ))

    return install


def test_health_and_routes(web_client, upstream):
    def handler(request):
        if request.url.path == "/health":
            return httpx.Response(200, json={"model_loaded": True, "faisal_loaded": True})
        assert request.headers["x-api-key"] == "test-model-key"
        if request.url.path == "/v1/style":
            return httpx.Response(200, json={"style": "firm", "router_source": "faisal"})
        payload = json.loads(request.content)
        assert payload["goal"] == SCENARIO["goal"]
        assert payload["message"] == SCENARIO["message"]
        assert payload["style"] == "حازم"
        assert len(payload["history"]) == 3
        return httpx.Response(200, json=GENERATED)

    upstream(handler)
    assert web_client.get("/").status_code == 200
    assert web_client.get("/coach.js").status_code == 200
    assert web_client.get("/api/model-health").json()["faisal_loaded"]
    assert web_client.post("/api/predict", json=SCENARIO).json()["method"] == "faisal"
    result = web_client.post("/api/reply", json={
        **SCENARIO, "tone": "formal", "style_key": "firm", "instruction": "اختصري الرد",
        "history": [{"role": "assistant", "content": "الرد الأول"}],
    })
    assert result.status_code == 200
    assert result.json()["reply"] == GENERATED["reply"]
    assert result.json()["coaching"] == GENERATED["coaching"]
    assert result.json()["mock"] is False


@pytest.mark.parametrize("payload", [[], {"reply": "مثال", "reply_source": "template"}, {"reply": " "}, {**GENERATED,"mock":True}])
def test_invalid_model_output(web_client, upstream, payload):
    upstream(lambda request: httpx.Response(200, json=payload))
    assert web_client.post("/api/reply", json=SCENARIO).status_code == 502


def test_register_edit_provenance_survives_the_web_bridge(web_client, upstream):
    upstream(lambda request: httpx.Response(200, json={
        **GENERATED,
        "draft_before_register_normalization": "لا أريد موعدا غير مؤكد",
        "register_normalization": ["لا أريد → ما أبي"],
    }))
    result = web_client.post("/api/reply", json=SCENARIO)
    assert result.status_code == 200
    assert result.json()["register_normalization"] == ["لا أريد → ما أبي"]
    assert result.json()["draft_before_register_normalization"] == "لا أريد موعدا غير مؤكد"
    assert result.json()["reply_source"] == "qwen_lora_generated"


def test_ollama_writer_keeps_its_actual_identity(web_client,upstream):
    upstream(lambda request:httpx.Response(200,json={**GENERATED,"reply_source":"ollama_generated","generator":"configured-writer (Ollama, Q4_K_M)"}))
    result=web_client.post('/api/reply',json=SCENARIO)
    assert result.status_code==200
    assert result.json()['reply_source']=='ollama_generated'
    assert result.json()['generator']=='configured-writer (Ollama, Q4_K_M)'


def test_upstream_timeout_and_invalid_history(web_client, upstream):
    def timeout(request):
        raise httpx.ReadTimeout("slow")

    upstream(timeout)
    assert web_client.post("/api/reply", json=SCENARIO).status_code == 504
    result = web_client.post("/api/reply", json={**SCENARIO, "history": [
        {"role": "system", "content": "invalid turn"},
    ]})
    assert result.status_code == 422


def test_model_auth_and_inference_failure(monkeypatch):
    class Engine:
        def load(self):
            return self

        def predict_style(self, *args):
            return "firm", "rule_fallback"

        def _one_generation(self, *args, **kwargs):
            raise RuntimeError("private test payload")

    monkeypatch.setenv("LABEQ_API_KEY", "key")
    monkeypatch.setattr(labeq_api, "get_engine", Engine)
    client = TestClient(labeq_api.app)
    assert client.post("/v1/reply", json=SCENARIO).status_code == 401
    result = client.post("/v1/reply", json=SCENARIO, headers={"X-API-Key": "key"})
    assert result.status_code == 503
    assert "private test payload" not in result.text


def test_bad_model_config_health(web_client, monkeypatch):
    monkeypatch.setenv("LABEQ_MODEL_API_URL", "http://inference.example")
    assert web_client.get("/api/model-health").json() == {
        "configured": True, "reachable": False, "model_loaded": False, "faisal_loaded": False,
    }


def test_munsit_timing_and_provider_failure(web_client, monkeypatch, upstream):
    monkeypatch.setattr(web, "TTS_PROVIDER", "munsit")
    monkeypatch.setattr(web, "MUNSIT_API_KEY", "test-munsit-key")
    monkeypatch.setattr(web, "MUNSIT_VOICE_ID", "test-maha")
    monkeypatch.setattr(web, "MUNSIT_BASE_URL", "https://api.munsit.com/api/v1")
    request = {"text": "أهلًا وسهلًا"}
    pcm = b"\x00\x01" * 100
    alignment = {"characters": ["أ"], "character_start_times_seconds": [0.0]}
    def munsit_response(request):
        if request.method == "GET":
            return httpx.Response(200, json=[{
                "voice_id": "test-maha", "name": "Maha", "gender": "female",
                "dialect": ["najdi"],
            }])
        return httpx.Response(200, text=json.dumps({
            "audio_base64": base64.b64encode(pcm).decode(), "alignment": alignment,
        }))

    upstream(munsit_response)
    audio = web_client.post("/api/speak", json=request).json()
    assert audio["voice"] == "Maha" and audio["sync_mode"] == "timestamps"
    assert audio["alignment"] == alignment
    with wave.open(io.BytesIO(base64.b64decode(audio["audio_base64"]))) as file:
        assert file.getframerate() == 48000
        assert file.readframes(100) == pcm
    upstream(lambda req: httpx.Response(402))
    assert web_client.post("/api/speak", json=request).status_code == 502
    upstream(lambda req: httpx.Response(200, json=[]))
    assert web_client.post("/api/speak", json=request).status_code == 503


def test_stt_success_empty_and_unsupported(web_client, monkeypatch, upstream):
    monkeypatch.setattr(web, "API_KEY", "test-scribe-key")
    audio = {"file": ("test.webm", b"\0" * 128, "audio/webm")}

    def handler(request):
        assert request.headers["xi-api-key"] == "test-scribe-key"
        assert b"scribe_v2" in request.content
        return httpx.Response(200, json={"text": " أبي أوضح حدودي "})

    upstream(handler)
    assert web_client.post("/api/transcribe", files=audio).json() == {"text": "أبي أوضح حدودي"}
    assert web_client.post("/api/transcribe", files={
        "file": ("invalid.txt", b"x" * 128, "text/plain"),
    }).status_code == 415
    upstream(lambda req: httpx.Response(200, json={"text": " "}))
    assert web_client.post("/api/transcribe", files=audio).status_code == 502


def test_web_rate_limit(web_client, monkeypatch, upstream):
    from collections import OrderedDict

    monkeypatch.setattr(web, "REQUEST_LIMIT", 1)
    monkeypatch.setattr(web, "request_windows", OrderedDict())
    upstream(lambda request: httpx.Response(200, json=GENERATED))
    assert web_client.post("/api/reply", json=SCENARIO).status_code == 200
    limited = web_client.post("/api/reply", json=SCENARIO)
    assert limited.status_code == 429
    assert int(limited.headers["retry-after"]) >= 1
    assert web_client.get("/api/capabilities").status_code == 200


def test_munsit_blocks_a_different_voice_before_synthesis(web_client, monkeypatch, upstream):
    monkeypatch.setattr(web, "TTS_PROVIDER", "munsit")
    monkeypatch.setattr(web, "MUNSIT_API_KEY", "test-key")
    monkeypatch.setattr(web, "MUNSIT_VOICE_ID", "wrong-voice")
    monkeypatch.setattr(web, "MUNSIT_BASE_URL", "https://api.munsit.com/api/v1")
    calls = []

    def handler(request):
        calls.append(request.method)
        return httpx.Response(200, json=[{
            "voice_id": "actual-maha", "name": "Maha", "gender": "female", "dialect": ["najdi"],
        }])

    upstream(handler)
    assert web_client.post("/api/speak", json={"text": "يا هلا"}).status_code == 503
    assert calls == ["GET"]
