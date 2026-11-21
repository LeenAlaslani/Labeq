"""Real local generation with a configurable Ollama model and separate Faisal routing."""
import json
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from LABEQ_V16_Coaching_Engine import reply_v16
from generation_limits import GenerationBudgetError
from labeq_engine import finish_reply
from writing_policy import read_policy


class OllamaEngine:
    reply_source = "ollama_generated"

    def __init__(self, router, model, base_url="http://127.0.0.1:11434", policy=None):
        parsed = urlparse(base_url)
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("Use an Ollama base URL without credentials, query or fragment")
        if parsed.scheme != "https" and not (
            parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1", "::1"}
        ):
            raise ValueError("Ollama requires HTTPS or loopback HTTP")
        if not isinstance(model, str) or not model.strip():
            raise ValueError("Configure an actual Ollama model tag")
        self.router, self.model_tag, self.base_url = router, model, base_url.rstrip("/")
        details = self._request("/api/show", {"model":model})
        capabilities = details.get("capabilities")
        if capabilities is not None and "completion" not in capabilities:
            raise ValueError("The configured Ollama model cannot generate messages")
        quant = details.get("details", {}).get("quantization_level", "unspecified precision")
        self.generator = f"{model} (Ollama, {quant})"
        if policy:
            self.writer_system,self.writer_examples=read_policy(policy)
        loaded=self._request("/api/generate",{
            "model":model,"keep_alive":300,"options":{"num_ctx":4096},
        })
        if loaded.get("done") is not True:
            raise RuntimeError("Ollama did not finish loading the configured writer")

    @property
    def model(self):
        return self.router.model

    @property
    def faisal_ready(self):
        return self.router.faisal_ready

    def load(self):
        return self

    def predict_style(self, message, relation, goal):
        return self.router.predict_style(message,relation,goal)

    def _request(self, endpoint, payload):
        request = Request(
            self.base_url+endpoint, data=json.dumps(payload,ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type":"application/json"}, method="POST",
        )
        with urlopen(request,timeout=120) as response:
            result=json.load(response)
        if not isinstance(result,dict) or result.get("error"):
            raise RuntimeError("Ollama did not return a successful model response")
        return result

    def _one_generation(self, messages, retry=False, use_adapter=True, max_tokens=256):
        # No response adapter is claimed: the Qwen3.5 Faisal LoRA is used only
        # by the separate router; the configured writer is identified above.
        result=self._request("/api/chat", {
            "model":self.model_tag, "messages":messages, "stream":False, "keep_alive":300,
            "options":{"temperature":0.2 if retry else 0, "seed":3407,
                       "num_predict":max_tokens, "num_ctx":4096, "repeat_penalty":1.0},
        })
        self.last_generation={"tokens":result.get("eval_count"),"done_reason":result.get("done_reason"),
                              "max_tokens":max_tokens,"model":result.get("model",self.model_tag)}
        text=result.get("message",{}).get("content")
        if not isinstance(text,str) or not text.strip():
            raise RuntimeError("Ollama did not generate a message")
        if result.get("done_reason")=="length":
            raise GenerationBudgetError(text)
        return finish_reply(text)

    reply=reply_v16
