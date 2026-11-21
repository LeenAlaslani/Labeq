"""Loopback FastAPI service for Qwen3.5-4B + Saudi LoRA on Apple Silicon."""
from contextlib import asynccontextmanager
import os
from pathlib import Path
import secrets

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException

from labeq_api import ReplyRequest, StyleRequest
from mlx_inference import MlxEngine


ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")


@asynccontextmanager
async def lifespan(app):
    secret_file = ROOT / ".local_api_key"
    secret = os.getenv("LABEQ_API_KEY") or (secret_file.read_text().strip() if secret_file.exists() else "")
    if len(secret) < 16:
        raise RuntimeError("Configure LABEQ_API_KEY or run bash prepare_local.sh")
    app.state.secret = secret
    app.state.engine = MlxEngine(
        os.getenv("LABEQ_MLX_MODEL", "mlx-community/Qwen3.5-4B-MLX-4bit"),
        os.getenv("LABEQ_MLX_ADAPTER_DIR", str(ROOT / "mlx_adapter")),
        os.getenv("LABEQ_MLX_FAISAL_DIR") or None,
        os.getenv("LABEQ_MLX_ADAPTER_LABEL", "Saudi LoRA"),
        editor_path=os.getenv("LABEQ_MLX_EDITOR_MODEL") or None,
    )
    yield


app = FastAPI(title="LABEQ MLX inference", lifespan=lifespan, docs_url=None, redoc_url=None)


@app.get("/health")
def health():
    engine = getattr(app.state, "engine", None)
    return {
        "service": "labeq-mac", "status": "online", "backend": "mlx-vlm",
        "model_loaded": engine is not None, "adapter_loaded": engine is not None,
        "faisal_loaded": bool(engine and engine.faisal_ready),
    }


def require_key(x_api_key: str | None):
    if not secrets.compare_digest(x_api_key or "", app.state.secret):
        raise HTTPException(401, "Unauthorized")


@app.post("/v1/style")
async def route_style(req: StyleRequest, x_api_key: str | None = Header(default=None)):
    require_key(x_api_key)
    style, source = app.state.engine.predict_style(req.message, req.relation, req.goal)
    return {"style": style, "router_source": source, "confidence": None}


@app.post("/v1/reply")
async def reply(req: ReplyRequest, x_api_key: str | None = Header(default=None)):
    require_key(x_api_key)
    try:
        # Keep MLX generation on the process thread used during startup.
        return app.state.engine.reply(
            req.message, req.relation, req.goal, req.style, req.speaker_gender,
            req.recipient_gender, [turn.model_dump() for turn in req.history], req.generation_mode,
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except Exception as exc:
        print("Local MLX generation failed:", type(exc).__name__, flush=True)
        raise HTTPException(503, "Local MLX inference failed") from exc
