"""Evidence-anchored model diagnostics, not an independent quality certificate."""
import json


def review_prompt(message, relation, goal, candidate, register):
    return (
        "راجع الرسالة مقابل طلب المستخدم. استخرج كل طلب وقيد مهم من النص الأصلي، "
        "وقيّم كل واحد منفصلا. فرّق بين الفعل المطلوب، والأثر على العلاقة، وما منع المستخدم إضافته. "
        "لا تختزل طلبات متعددة إلى عنوان عام. لا تضف شروطا من عندك ولا تطلب عذرا أو وعدا لم يطلبه المستخدم. "
        "source_quote اقتباس حرفي قصير من الموقف أو الهدف يثبت الشرط. "
        "status إما met أو missing أو contradicted. reason سبب قصير يصف الخلل إن وجد. "
        "unsupported قائمة اقتباسات حرفية من الرسالة تتضمن حقائق أو أعذارا أو وعودا غير مسندة، "
        "وليست مجرد اختلاف في الأسلوب. إذا لا يوجد خلها فارغة. "
        "اكتب JSON فقط بهذا الشكل: "
        '{"checks":[{"source_quote":"...","status":"met","reason":""}],"unsupported":[]}\n'
        f"طريقة الكتابة: {register}\nالموقف: {message}\nالعلاقة: {relation}\nالهدف: {goal}\nالرسالة: {candidate}"
    )


def parse_review(text, message, goal, candidate):
    """Reject malformed, truncated or ungrounded judgments instead of calling them a pass."""
    result = {"valid":False, "checks":[], "unsupported":[], "issues":[]}
    raw = (text or "").strip()
    if raw.startswith("```json") and raw.endswith("```"):
        raw = raw[7:-3].strip()
    try:
        obj = json.loads(raw)
        if not isinstance(obj,dict) or set(obj)!={"checks","unsupported"}:
            raise ValueError("schema")
        if not isinstance(obj["checks"],list) or not 1 <= len(obj["checks"]) <= 12:
            raise ValueError("checks")
        if not isinstance(obj["unsupported"],list) or len(obj["unsupported"])>8:
            raise ValueError("unsupported")
        source = message + "\n" + goal
        seen = set()
        for check in obj["checks"]:
            if not isinstance(check,dict) or set(check)!={"source_quote","status","reason"}:
                raise ValueError("check schema")
            quote,status,reason = (check[k] for k in ("source_quote","status","reason"))
            if not all(isinstance(x,str) for x in (quote,status,reason)):
                raise ValueError("types")
            if len(quote.strip())<4 or quote not in source or quote in seen:
                raise ValueError("ungrounded or duplicated source")
            if status not in {"met","missing","contradicted"} or len(reason)>220:
                raise ValueError("status or reason")
            if status!="met" and not reason.strip():
                raise ValueError("missing reason")
            seen.add(quote)
        if any(not isinstance(q,str) or len(q.strip())<4 or q not in candidate for q in obj["unsupported"]):
            raise ValueError("ungrounded candidate quote")
        issues = [f"{c['source_quote']}: {c['reason']}" for c in obj["checks"] if c["status"]!="met"]
        issues += ["تفصيل غير مسند في الرسالة: " + q for q in obj["unsupported"]]
        result.update(valid=True,checks=obj["checks"],unsupported=obj["unsupported"],issues=issues)
    except (ValueError, TypeError, KeyError):
        result["error"]="invalid_or_ungrounded_review"
    return result
