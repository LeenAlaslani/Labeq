"""CPU fixture checks of the Gradio queue used by the ZeroGPU frontend."""
import json

import pytest
from fastapi.testclient import TestClient

pytest.importorskip("gradio")

from app import app
from cloud.space_app import create_app
import cloud.space_app as space_module


class FixtureEngine:
    model = object()
    faisal_ready = True
    adapter_revision = "fixture-revision"
    generator = "test fixture"

    def load(self):
        return self

    def predict_style(self, *args):
        return "firm", "faisal"

    def _one_generation(self, messages, retry=False, use_adapter=True, max_tokens=256):
        if use_adapter:
            return "ما أقدر أساعدك كل يوم، عندي شغلي وأحتاج أركز عليه."
        if "أربع سطور" in messages[-1]["content"]:
            return "جوهر الموقف: تتكرر طلبات المساعدة\nالخطوة: توضيح حدود المساعدة"
        return "النتيجة: مناسب"


def test_queued_reply_and_real_interface(monkeypatch,tmp_path):
    monkeypatch.setattr(app.state, "gradio_model", None, raising=False)
    (tmp_path/'source-manifest.json').write_text(json.dumps({'source_commit':'a'*40}))
    monkeypatch.setattr(space_module,'ROOT',tmp_path)
    configured = create_app(FixtureEngine(), lambda function: function)
    try:
        with TestClient(configured) as client:
            page = client.get("/")
            assert page.status_code == 200 and "space_client.js" in page.text
            capabilities = client.get("/api/capabilities").json()
            assert capabilities["model_transport"] == "gradio"
            health=client.get("/api/model-health").json()
            assert health["faisal_loaded"]
            assert health['source_commit']=='a'*40
            submitted = client.post("/model/gradio_api/call/reply", json={"data": [{
                "message": "زميلتي تطلب مساعدتي كل يوم وأنا عندي شغلي",
                "relation": "عمل", "goal": "أوضح حدودي", "generation_mode": "مولّد فقط",
            }]})
            assert submitted.status_code == 200, submitted.text
            result = client.get("/model/gradio_api/call/reply/" + submitted.json()["event_id"])
            assert "event: complete" in result.text, result.text
            payload = json.loads(result.text.split("event: complete\ndata: ")[1].split("\n")[0])[0]
            assert payload["router_source"] == "faisal"
            assert payload["reply_source"] == "qwen_lora_generated"
            assert "كل يوم" in payload["reply"]
    finally:
        app.state.gradio_model = None
