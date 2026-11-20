"""LABEQ showcase API. TTS/STT keys stay on this server, never in browser code."""
import os
import base64
import io
import json
import wave
from collections import OrderedDict, deque
from time import monotonic
from xml.sax.saxutils import escape
from pathlib import Path
from typing import Literal
from model_bridge import remote_reply, remote_style, remote_health, configured, request_payload
from setup_munsit import get_voice_list, select_maha

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

# Zariyah: official Microsoft Saudi Arabic female neural voice.
TTS_PROVIDER = os.environ.get("LABEQ_TTS_PROVIDER", "munsit").strip().lower()
AZURE_KEY = os.environ.get("AZURE_SPEECH_KEY", "").strip()
AZURE_REGION = os.environ.get("AZURE_SPEECH_REGION", "").strip().lower()
AZURE_VOICE = "ar-SA-ZariyahNeural"
MUNSIT_API_KEY = os.environ.get("MUNSIT_API_KEY", "").strip()
MUNSIT_VOICE_ID = os.environ.get("MUNSIT_VOICE_ID", "").strip()
MUNSIT_BASE_URL = os.environ.get("MUNSIT_BASE_URL", "https://api.munsit.com/api/v1").strip().rstrip("/")
MUNSIT_STABILITY = float(os.environ.get("MUNSIT_STABILITY", "0.44"))
MUNSIT_SPEED = float(os.environ.get("MUNSIT_SPEED", "0.95"))
MUNSIT_MODEL_ID = "faseeh-v1-preview"
# Endpoint is fixed to the two official regions; avoid sending secret keys to untrusted URLs.
ALLOWED_MUNSIT_BASES = {
    "https://api.munsit.com/api/v1",
    "https://ae.api.faseeh.ai/api/v1",
}
API_KEY = os.environ.get("ELEVENLABS_API_KEY", "").strip()
VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID", "").strip()
TTS_MODEL = os.environ.get("ELEVENLABS_MODEL_ID", "eleven_multilingual_v2").strip()
VOICE_ENABLED = os.environ.get("LABEQ_VOICE_ENABLED", "1") == "1"
MODEL_MODE = os.environ.get("LABEQ_MODEL_MODE", "real" if configured() else "demo").lower()

app = FastAPI(title="LABEQ Experience", version="0.1.0")
REQUEST_LIMIT = max(0, int(os.getenv("LABEQ_REQUESTS_PER_MINUTE", "30")))
LIMITED_PATHS = {"/api/reply", "/api/predict", "/api/speak", "/api/transcribe", "/model/gradio_api/call/reply"}
request_windows = OrderedDict()


@app.middleware("http")
async def limit_expensive_requests(request: Request, call_next):
    if REQUEST_LIMIT and request.method == "POST" and request.url.path in LIMITED_PATHS:
        address = request.client.host if request.client else "unknown"
        now = monotonic()
        window = request_windows.pop(address, deque())
        request_windows[address] = window
        if len(request_windows) > 2048:
            request_windows.popitem(last=False)
        while window and now - window[0] >= 60:
            window.popleft()
        if len(window) >= REQUEST_LIMIT:
            retry_after = max(1, int(60 - (now - window[0])) + 1)
            return JSONResponse(
                {"detail": "طلبات كثيرة. انتظري قليلًا ثم حاولي مرة ثانية."},
                status_code=429, headers={"Retry-After": str(retry_after)},
            )
        window.append(now)
    return await call_next(request)


class PredictionRequest(BaseModel):
    message: str = Field(min_length=2, max_length=1500)
    relation: Literal["friend", "work", "family", "customer"]
    goal: str = Field(min_length=2, max_length=180)


class Turn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=500)


class LabeqReplyRequest(BaseModel):
    message: str = Field(min_length=2, max_length=1500)
    relation: Literal["friend", "work", "family", "customer"]
    goal: str = Field(min_length=2, max_length=180)
    tone: Literal["casual", "formal"] = "casual"
    style_key: Literal["polite", "firm", "diplomatic", "apology", "clarify"] | None = None
    history: list[Turn] = Field(default_factory=list, max_length=4)
    instruction: str | None = Field(default=None, max_length=500)


class SpeechRequest(BaseModel):
    text: str = Field(min_length=1, max_length=600)


@app.get("/")
def home():
    return FileResponse(ROOT / "index.html")


@app.get("/styles.css")
def stylesheet():
    return FileResponse(ROOT / "styles.css", media_type="text/css")


@app.get("/app.js")
def client_script():
    return FileResponse(ROOT / "app.js", media_type="text/javascript")


@app.get("/space_client.js")
def space_client_script():
    return FileResponse(ROOT / "space_client.js", media_type="text/javascript")


@app.get("/coach.js")
def communication_coach_script():
    return FileResponse(ROOT / "coach.js", media_type="text/javascript")


@app.get("/api/capabilities")
def capabilities():
    if TTS_PROVIDER == "munsit":
        voice_enabled = bool(
            MUNSIT_API_KEY and MUNSIT_VOICE_ID and MUNSIT_BASE_URL in ALLOWED_MUNSIT_BASES
            and monotonic() >= getattr(app.state, "voice_retry_after", 0)
        )
        voice_label = "مها · نجدية — منصت"
    elif TTS_PROVIDER == "azure":
        voice_enabled = bool(AZURE_KEY and AZURE_REGION)
        voice_label = "زاريّة — سعودية"
    elif TTS_PROVIDER == "elevenlabs":
        voice_enabled = bool(API_KEY and VOICE_ID)
        voice_label = "ElevenLabs"
    else:
        voice_enabled = False
        voice_label = "صوت غير مهيأ"
    voice_enabled = voice_enabled and VOICE_ENABLED
    gradio_model = getattr(app.state, "gradio_model", None)
    return {
        "model_transport": "gradio" if gradio_model else "http",
        "tts": voice_enabled,
        "tts_provider": TTS_PROVIDER,
        "voice_name": voice_label,
        "stt": bool(API_KEY),
        "model_mode": MODEL_MODE,
        "model_configured": bool(gradio_model) or configured(),
    }


@app.get("/api/model-health")
async def model_health():
    gradio_model = getattr(app.state, "gradio_model", None)
    if gradio_model:
        return {"configured": True, "reachable": True, **gradio_model}
    if MODEL_MODE != "real":
        return {"configured": False, "reachable": False, "model_loaded": False, "faisal_loaded": False}
    return await remote_health()


@app.post("/api/reply")
async def reply_from_model(req: LabeqReplyRequest):
    if getattr(app.state, "gradio_model", None):
        raise HTTPException(409, "Use the queued /model/gradio_api/call/reply endpoint")
    if MODEL_MODE != "real":
        raise HTTPException(503, "المودل الحقيقي غير مفعّل. شغّلي خادم API على الماك أو Colab وربطيه بلبِق.")
    payload = request_payload(req.message, req.relation, req.goal, req.style_key, req.tone,
                              [turn.model_dump() for turn in req.history], req.instruction)
    return await remote_reply(payload)


@app.post("/api/predict")
async def predict(req: PredictionRequest):
    # Intentional UI-only demonstration. This is NOT Faisal inference.
    if MODEL_MODE == "demo":
        # Demonstration rules ONLY. These outputs are NOT Faisal model predictions.
        lower = req.goal.lower()
        if "أرفض" in lower or "اعتذر عن الطلب" in lower:
            style = "polite"
        elif "حدود" in lower or "مسؤولياتي" in lower:
            style = "firm"
        elif "خلاف" in lower or "تفاهم" in lower or "أحل" in lower or "سوء الفهم" in lower:
            style = "diplomatic"
        elif "أعتذر" in lower or "خطأ" in lower:
            style = "apology"
        elif "أفهم" in lower or "توضيح" in lower or "المقصود" in lower:
            style = "clarify"
        else:
            style = "clarify"
        return {"style": style, "confidence": None, "mock": True, "method": "rule_based_demo"}

    return await remote_style(request_payload(req.message, req.relation, req.goal))


def _pcm_to_wav(pcm: bytes, sample_rate: int = 48000) -> bytes:
    """Wrap Munsit's headerless signed PCM16 mono in a playable WAV container."""
    with io.BytesIO() as output:
        with wave.open(output, "wb") as stream:
            stream.setnchannels(1)
            stream.setsampwidth(2)
            stream.setframerate(sample_rate)
            stream.writeframes(pcm)
        return output.getvalue()


async def munsit_speak(text: str) -> dict:
    """Synthesize new text using the public Maha voice ID configured by setup_munsit.py."""
    if not MUNSIT_API_KEY or not MUNSIT_VOICE_ID:
        raise HTTPException(503, "Munsit is not configured. Run: python setup_munsit.py")
    if MUNSIT_BASE_URL not in ALLOWED_MUNSIT_BASES:
        raise HTTPException(500, "Unrecognized Munsit region endpoint.")
    base = f"{MUNSIT_BASE_URL}/text-to-speech/{MUNSIT_MODEL_ID}"
    payload = {
        "voice_id": MUNSIT_VOICE_ID,
        "text": text,
        "stability": MUNSIT_STABILITY,
        "speed": MUNSIT_SPEED,
        "sample_rate": 48000,
    }
    headers = {"x-api-key": MUNSIT_API_KEY, "Content-Type": "application/json"}
    try:
        async with httpx.AsyncClient(timeout=100.0) as client:
            voices = await client.get(f"{MUNSIT_BASE_URL}/voices", headers=headers)
            voices.raise_for_status()
            try:
                maha, _ = select_maha(get_voice_list(voices.json()))
            except (ValueError, TypeError, AttributeError) as exc:
                raise HTTPException(503, "Maha voice identity could not be verified.") from exc
            if str(maha["voice_id"]) != MUNSIT_VOICE_ID:
                raise HTTPException(503, "Configured voice does not match the approved Maha voice.")
            response = await client.post(f"{base}/with-timestamps", headers=headers, json=payload)
            if response.status_code == 400 and "timestamps are not available" in response.text.lower():
                # Some models do not offer timings; still return real audio, never fake timestamps.
                fallback = await client.post(base, headers=headers, json=payload)
                fallback.raise_for_status()
                if not fallback.content or not fallback.content.startswith(b"RIFF"):
                    raise HTTPException(502, "Munsit returned audio in an unexpected format.")
                return {
                    "audio_base64": base64.b64encode(fallback.content).decode("ascii"),
                    "audio_mime": "audio/wav",
                    "alignment": {},
                    "sync_mode": "approximate",
                    "voice": "Maha",
                }
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        if status == 401:
            msg = "Munsit API key is not valid for this region."
        elif status == 402:
            app.state.voice_retry_after = monotonic() + 300
            msg = "Munsit wallet has insufficient credits."
        elif status == 429:
            msg = "Munsit rate limit reached."
        else:
            msg = f"Munsit TTS returned HTTP {status}."
        raise HTTPException(502, msg) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(502, "Could not connect to Munsit TTS.") from exc

    chunks = []
    alignment = None
    try:
        for line in response.text.splitlines():
            if not line.strip():
                continue
            event = json.loads(line)
            if not isinstance(event, dict):
                raise ValueError("Expected an audio event object")
            if event.get("audio_base64"):
                chunks.append(base64.b64decode(event["audio_base64"], validate=True))
            if event.get("alignment"):
                alignment = event["alignment"]
    except (ValueError, KeyError, TypeError) as exc:
        raise HTTPException(502, "Munsit returned invalid audio timing data.") from exc
    pcm = b"".join(chunks)
    if len(pcm) < 128 or len(pcm) % 2:
        raise HTTPException(502, "Munsit returned incomplete PCM audio.")
    if not isinstance(alignment, dict) or alignment.get("aligned") is False:
        alignment = {}
    audio_wav = _pcm_to_wav(pcm, 48000)
    return {
        "audio_base64": base64.b64encode(audio_wav).decode("ascii"),
        "audio_mime": "audio/wav",
        "alignment": alignment,
        "sync_mode": "timestamps" if alignment else "approximate",
        "voice": "Maha",
    }


@app.post("/api/speak")
async def speak(req: SpeechRequest):
    if not VOICE_ENABLED:
        raise HTTPException(503, "Maha voice is inactive.")
    if TTS_PROVIDER == "munsit":
        return await munsit_speak(req.text)
    if TTS_PROVIDER == "azure":
        if not AZURE_KEY or not AZURE_REGION:
            raise HTTPException(503, "Azure Speech not configured. Set AZURE_SPEECH_KEY and AZURE_SPEECH_REGION on the server.")
        if not all(c.isalnum() or c == "-" for c in AZURE_REGION):
            raise HTTPException(500, "Invalid Azure Speech region setting.")
        # XML-escape user-supplied names and messages to prevent malformed SSML.
        ssml = ("<speak version='1.0' xml:lang='ar-SA'>"
                "<voice name='ar-SA-ZariyahNeural'>"
                f"{escape(req.text)}"
                "</voice></speak>")
        url = f"https://{AZURE_REGION}.tts.speech.microsoft.com/cognitiveservices/v1"
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                res = await client.post(
                    url,
                    headers={
                        "Ocp-Apim-Subscription-Key": AZURE_KEY,
                        "Content-Type": "application/ssml+xml",
                        "X-Microsoft-OutputFormat": "audio-24khz-48kbitrate-mono-mp3",
                        "User-Agent": "LABEQ-Showcase",
                    },
                    content=ssml.encode("utf-8"),
                )
                res.raise_for_status()
                audio_bytes = res.content
        except httpx.HTTPStatusError as exc:
            raise HTTPException(502, f"Azure TTS HTTP {exc.response.status_code}") from exc
        except httpx.HTTPError as exc:
            raise HTTPException(502, "Azure TTS is unavailable") from exc
        if not audio_bytes:
            raise HTTPException(502, "Azure TTS returned empty audio.")
        # Azure REST returns MP3, but no word timestamps. Frontend uses
        # approximate highlighting based on playback duration (not phoneme sync).
        return {
            "audio_base64": base64.b64encode(audio_bytes).decode("ascii"),
            "audio_mime": "audio/mpeg",
            "alignment": {},
            "sync_mode": "approximate",
            "voice": AZURE_VOICE,
        }

    if TTS_PROVIDER != "elevenlabs":
        raise HTTPException(500, "Unknown LABEQ_TTS_PROVIDER setting")
    if not API_KEY or not VOICE_ID:
        raise HTTPException(503, "ElevenLabs voice not configured.")
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}/with-timestamps"
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            res = await client.post(
                url,
                headers={"xi-api-key": API_KEY, "content-type": "application/json"},
                json={
                    "text": req.text,
                    "model_id": TTS_MODEL,
                    "voice_settings": {"stability": 0.55, "similarity_boost": 0.78},
                },
            )
            res.raise_for_status()
            result = res.json()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(502, f"ElevenLabs TTS HTTP {exc.response.status_code}") from exc
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(502, "ElevenLabs TTS unavailable or returned invalid data") from exc
    if not result.get("audio_base64"):
        raise HTTPException(502, "ElevenLabs response has no audio.")
    return {
        "audio_base64": result["audio_base64"],
        "audio_mime": "audio/mpeg",
        "alignment": result.get("alignment") or result.get("normalized_alignment") or {},
        "sync_mode": "timestamps",
    }


@app.post("/api/transcribe")
async def transcribe(file: UploadFile = File(...)):
    if not API_KEY:
        raise HTTPException(503, "ElevenLabs Scribe not configured.")
    audio = await file.read(10 * 1024 * 1024 + 1)
    if len(audio) > 10 * 1024 * 1024:
        raise HTTPException(413, "Maximum audio size is 10 MB.")
    if len(audio) < 100:
        raise HTTPException(400, "Recording is empty.")
    mime = file.content_type or "audio/webm"
    if not (mime.startswith("audio/") or mime == "video/webm" or mime == "application/octet-stream"):
        raise HTTPException(415, "File must be audio.")
    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            res = await client.post(
                "https://api.elevenlabs.io/v1/speech-to-text",
                headers={"xi-api-key": API_KEY},
                data={"model_id": "scribe_v2", "language_code": "ara"},
                files={"file": (file.filename or "scenario.webm", audio, mime)},
            )
            res.raise_for_status()
            output = res.json()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(502, f"ElevenLabs Scribe HTTP {exc.response.status_code}") from exc
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(502, "Speech recognition service unavailable") from exc
    text = output.get("text") if isinstance(output, dict) else None
    if not isinstance(text, str) or not text.strip():
        raise HTTPException(502, "Speech recognition returned no text")
    return {"text": text.strip()}


@app.get("/character2d.js")
def character_script():
    return FileResponse(ROOT / "character2d.js", media_type="text/javascript")

@app.get("/assets/{asset_name}")
def character_asset(asset_name: str):
    allowed = {"maha_character_original.png", "maha_character_base.png", "maha_character_body.png", "maha_character_arm.png", "maha_mouth_open.png", "maha_body_original_face.png", "maha_body_blink.png", "maha_mouth_clean_overlay.png", "expression_greet.jpg", "expression_happy.jpg", "expression_think.jpg", "expression_sorry.jpg", "expression_surprised.jpg"}
    if asset_name not in allowed:
        raise HTTPException(404, "Unknown asset")
    return FileResponse(ROOT / "assets" / asset_name)
