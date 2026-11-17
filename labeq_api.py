"""API endpoints: GET /health and POST /v1/reply.
Run on a persistent GPU service, not as a public Colab localhost URL.
"""
from __future__ import annotations
import os
import secrets
from contextlib import asynccontextmanager
from functools import lru_cache
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from labeq_engine import LabeqEngine, ALLOWED_USER_STYLES
from LABEQ_V16_Coaching_Engine import reply_v16

@asynccontextmanager
async def lifespan(app):
    if os.getenv("LABEQ_PRELOAD") == "1":
        get_engine().load()
    yield


app = FastAPI(title="لبق API", version="1.0.0", docs_url=None, redoc_url=None, lifespan=lifespan)
allowed_origins = [x.strip() for x in os.getenv("LABEQ_CORS_ORIGINS", "").split(",") if x.strip()]
app.add_middleware(CORSMiddleware, allow_origins=allowed_origins, allow_methods=["POST", "GET"], allow_headers=["X-API-Key", "Content-Type"])

class Turn(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(min_length=1, max_length=500)

class StyleRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    relation: str = Field(default="شخص آخر", max_length=100)
    goal: str = Field(default="أبي رد مناسب", max_length=300)


class ReplyRequest(StyleRequest):
    style: str = Field(default="تلقائي", max_length=40)
    speaker_gender: str = Field(default="غير محدد")
    recipient_gender: str = Field(default="غير محدد")
    history: list[Turn] = Field(default_factory=list, max_length=6)
    generation_mode: str = Field(default="موجّه", pattern="^(موجّه|مولّد فقط)$")

@lru_cache(maxsize=1)
def get_engine():
    return LabeqEngine(
        adapter_dir=os.environ.get("LABEQ_ADAPTER_DIR", "/content/Labeq_Qwen35_4B_Pilot_LoRA"),
        use_faisal=os.environ.get("LABEQ_USE_FAISAL", "0") == "1",
        faisal_path=os.getenv("LABEQ_FAISAL_PATH") or None,
    )

@app.get("/health")
def health():
    engine = get_engine()
    return {"service": "labeq", "status": "online", "model_loaded": engine.model is not None,
            "faisal_loaded": engine.faisal_ready}

def require_key(x_api_key: str | None):
    configured_key = os.getenv("LABEQ_API_KEY")
    if not configured_key and os.getenv("LABEQ_DEV_MODE") != "1":
        raise HTTPException(503, "LABEQ_API_KEY must be configured")
    if configured_key and not secrets.compare_digest(x_api_key or "", configured_key):
        raise HTTPException(401, "Unauthorized")


@app.post("/v1/style")
def route_style(req: StyleRequest, x_api_key: str | None = Header(default=None)):
    require_key(x_api_key)
    try:
        style, source = get_engine().predict_style(req.message, req.relation, req.goal)
    except Exception as exc:
        raise HTTPException(503, "Model unavailable or style prediction failed") from exc
    return {"style": style, "router_source": source, "confidence": None}


@app.post("/v1/reply")
def reply(req: ReplyRequest, x_api_key: str | None = Header(default=None)):
    require_key(x_api_key)
    if req.style not in ALLOWED_USER_STYLES:
        raise HTTPException(422, "Unsupported style")
    try:
        return reply_v16(
            get_engine(), req.message, req.relation, req.goal, req.style,
            req.speaker_gender, req.recipient_gender,
            [x.model_dump() for x in req.history],
            generation_mode=req.generation_mode,
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except Exception as exc:
        # Avoid logging raw user-provided conversations.
        print("LABEQ request failed:", type(exc).__name__)
        raise HTTPException(503, "Model unavailable or inference failed") from exc
