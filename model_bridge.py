"""Server-side bridge to the exact Colab /v1/reply API. No generated data fallback."""
from __future__ import annotations
import os
from urllib.parse import urlparse
import httpx
from fastapi import HTTPException

ALLOWED_KEYS = {"polite", "firm", "diplomatic", "apology", "clarify"}
STYLE_AR = {
    "polite": "لطيف", "firm": "حازم", "diplomatic": "دبلوماسي",
    "apology": "اعتذار", "clarify": "طلب توضيح",
}
STYLE_ALIASES = {v: k for k, v in STYLE_AR.items()}
RELATION_AR = {"friend": "صديق", "family": "عائلة", "work": "عمل", "customer": "عميل"}


def model_url() -> str:
    return os.getenv("LABEQ_MODEL_API_URL", "").strip().rstrip("/")


def configured() -> bool:
    return bool(model_url() and os.getenv("LABEQ_MODEL_API_KEY", "").strip())


def checked_base() -> str:
    base = model_url()
    try:
        uri = urlparse(base)
        host, port = uri.hostname, uri.port
    except ValueError as exc:
        raise HTTPException(503, "رابط خادم المودل غير صالح.") from exc
    is_local = host in {"127.0.0.1", "localhost"}
    if not host or port == 0 or uri.username or uri.password or uri.query or uri.fragment or uri.scheme not in ({"https", "http"} if is_local else {"https"}):
        raise HTTPException(503, "رابط المودل غير صحيح: استخدمي HTTPS أو localhost.")
    if base.endswith("/v1/reply"):
        base = base[:-len("/v1/reply")]
    return base


def request_payload(message: str, relation: str, goal: str, style_key: str | None = None, tone: str = "casual", history: list | None = None, instruction: str | None = None) -> dict:
    # The model notebook accepts Arabic relationship and user style choices.
    style = STYLE_AR.get(style_key, "تلقائي") if style_key else "تلقائي"
    turns = list(history or [])
    if tone == "formal":
        # Formality and communication style are independent dimensions.
        # Do not override "apology"/"firm"/etc. with an entirely different style.
        turns.append({"role": "user", "content": "تعليمات تعديل الرد: اجعلي الصياغة رسمية ومهنية دون تغيير الهدف أو نوع الأسلوب."})
    if instruction:
        # Keep the original scenario intact. A rewrite request is NOT a new
        # fact about the social situation; pass it separately in the history.
        turns.append({"role": "user", "content": "تعليمات تعديل الرد: " + instruction[:450]})
    return {
        "message": message,
        "relation": RELATION_AR.get(relation, "شخص آخر"),
        "goal": goal,
        "style": style,
        "speaker_gender": "غير محدد",
        "recipient_gender": "غير محدد",
        "history": turns[-6:],
        # This prevents curated fixed references from posing as generated replies.
        "generation_mode": "مولّد فقط",
    }


async def _remote_post(endpoint: str, payload: dict) -> dict:
    if not configured():
        raise HTTPException(503, "المودل لم يُربط بعد. اضبطي رابط API والمفتاح في .env.")
    url = checked_base() + endpoint
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(150.0, connect=15.0), follow_redirects=False) as client:
            res = await client.post(url, headers={"X-API-Key": os.getenv("LABEQ_MODEL_API_KEY", "")}, json=payload)
    except httpx.TimeoutException as exc:
        raise HTTPException(504, "المودل تأخر في الرد. تحققي من خادم GPU أو MLX.") from exc
    except httpx.RequestError as exc:
        raise HTTPException(503, "تعذر الوصول إلى خادم المودل. تحققي من الرابط والمنفذ.") from exc
    if res.status_code == 401:
        raise HTTPException(503, "مفتاح API الخاص بالمودل غير صحيح.")
    if res.status_code >= 400:
        raise HTTPException(503, f"خادم المودل رجّع خطأ HTTP {res.status_code}.")
    try:
        data = res.json()
    except ValueError as exc:
        raise HTTPException(502, "استجابة المودل ليست JSON صالحًا.") from exc
    if not isinstance(data, dict):
        raise HTTPException(502, "استجابة المودل ليست كائن JSON صالحًا.")
    return data


async def remote_style(payload: dict) -> dict:
    data = await _remote_post("/v1/style", {key: payload[key] for key in ("message", "relation", "goal")})
    style, source = data.get("style"), data.get("router_source")
    if not isinstance(style, str) or style not in ALLOWED_KEYS or source not in ("faisal", "rule_fallback"):
        raise HTTPException(502, "خادم المودل لم يرجع أسلوبًا صالحًا.")
    return {"style": style, "confidence": None, "mock": False, "method": source}


async def remote_reply(payload: dict) -> dict:
    data = await _remote_post("/v1/reply", payload)
    reply = data.get("reply")
    if not isinstance(reply, str) or not reply.strip():
        raise HTTPException(502, "المودل لم يُرجع نص رد صالحًا.")
    source = data.get("reply_source", "unknown")
    if source not in {"qwen_lora_generated","qwen_base_generated","ollama_generated"} or data.get("mock") is True:
        # Explicitly reject curated responses in real-only UI mode.
        raise HTTPException(502, "المودل لم يرجع ردًا مولدًا من خادم حقيقي مدعوم.")
    key = data.get("style_key")
    if not isinstance(key, str) or key not in ALLOWED_KEYS:
        label = data.get("style_used")
        key = STYLE_ALIASES.get(label) if isinstance(label, str) else None
    router = data.get("router_source") or "unknown"
    coaching = data.get("coaching") if isinstance(data.get("coaching"), dict) else {}
    safe_coaching = {k: str(coaching[k])[:180] for k in ("core", "objective", "strategy", "risk")
                     if k in coaching and isinstance(coaching[k], str)}
    warnings = data.get("quality_warnings")
    register_edits = data.get("register_normalization")
    raw_draft = data.get("draft_before_register_normalization")
    return {
        "reply": reply.strip(), "style": key,
        "coaching": safe_coaching,
        "review_status": data.get("review_status", "unverified"),
        "style_used": data.get("style_used") or "غير محدد",
        "router_source": router, "reply_source": source,
        "register_normalization": [item[:200] for item in register_edits if isinstance(item, str)][:20]
        if isinstance(register_edits, list) else [],
        "draft_before_register_normalization": raw_draft[:1200] if isinstance(raw_draft, str) else None,
        "needs_review": bool(data.get("needs_review", False)),
        "was_retried": data.get("was_retried") is True,
        "quality_warnings": [item[:180] for item in warnings if isinstance(item, str)][:5]
        if isinstance(warnings, list) else [],
        "generator": data.get("generator") if isinstance(data.get("generator"), str) else None,
        "mock": False,
    }


async def remote_health() -> dict:
    if not configured():
        return {"configured": False, "reachable": False, "model_loaded": False, "faisal_loaded": False}
    try:
        async with httpx.AsyncClient(timeout=8.0, follow_redirects=False) as client:
            res = await client.get(checked_base() + "/health")
            res.raise_for_status()
            d = res.json()
            return {"configured": True, "reachable": True,
                    "model_loaded": d.get("model_loaded") is True,
                    "faisal_loaded": d.get("faisal_loaded") is True}
    except (httpx.HTTPError, HTTPException, ValueError, AttributeError):
        return {"configured": True, "reachable": False, "model_loaded": False, "faisal_loaded": False}
