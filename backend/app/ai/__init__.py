"""AI ENGINE — decoupled explanation layer.

Default: deterministic rule-based narrative (no API needed).
Optional: Anthropic or OpenAI via .env (AI_PROVIDER=anthropic|openai + key). The LLM receives
only computed facts and must return the same JSON sections. It never decides BUY/SELL; outputs
that contain recommendations are rejected and the rules engine is used instead.
"""
from __future__ import annotations

import json
import logging
import re

import httpx

from ..config import get_settings
from .rules import SECTIONS, rules_analysis

log = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a cautious financial research assistant. You explain context, risks and contradictions "
    "about a publicly disclosed congressional stock transaction. Rules: (1) Never recommend buying, "
    "selling or holding. (2) Never claim to know why the filer traded; say 'may' / 'could'. "
    "(3) Use only the facts provided; if a datum is labelled mock or unavailable, say so. "
    "(4) Reply ONLY with a JSON object whose keys are exactly: " + ", ".join(SECTIONS) +
    "; each value is an array of 2-4 concise bullet strings."
)
_FORBIDDEN = re.compile(r"\b(you should|we recommend|i recommend|strong buy|must buy|must sell)\b", re.I)


def _facts(a: dict, ctx: dict) -> str:
    keep = {k: a[k] for k in ("ticker", "company", "transaction_type", "asset_type", "transaction_date",
                              "disclosure_date", "delay_days", "amount_min", "amount_max", "strike", "expiration",
                              "price_at_transaction", "price_at_disclosure", "price_now", "confidence_level")}
    keep["decay"] = a["decay"]
    keep["score"] = {"score": a["score"]["score"], "classification": a["score"]["classification"],
                     "components": [{c["label"]: c["score"], "detail": c["detail"]} for c in a["score"]["components"]]}
    keep["technicals"] = {k: v for k, v in ctx["tech"].items() if k != "momentum"}
    keep["momentum"] = ctx["tech"].get("momentum")
    keep["fundamentals"] = ctx["fundamentals"]
    return json.dumps(keep, default=str)


def _parse(text: str) -> dict | None:
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return None
    try:
        d = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    if not all(k in d and isinstance(d[k], list) for k in SECTIONS):
        return None
    if _FORBIDDEN.search(json.dumps(d)):
        return None
    return {k: [str(x) for x in d[k]][:5] for k in SECTIONS}


def _anthropic(facts: str) -> dict | None:
    s = get_settings()
    r = httpx.post("https://api.anthropic.com/v1/messages", timeout=60, headers={
        "x-api-key": s.anthropic_api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
        json={"model": s.anthropic_model, "max_tokens": 1500, "system": SYSTEM_PROMPT,
              "messages": [{"role": "user", "content": f"FACTS:\n{facts}"}]})
    r.raise_for_status()
    return _parse("".join(b.get("text", "") for b in r.json().get("content", [])))


def _openai(facts: str) -> dict | None:
    s = get_settings()
    r = httpx.post("https://api.openai.com/v1/chat/completions", timeout=60,
                   headers={"Authorization": f"Bearer {s.openai_api_key}"},
                   json={"model": s.openai_model, "response_format": {"type": "json_object"},
                         "messages": [{"role": "system", "content": SYSTEM_PROMPT},
                                      {"role": "user", "content": f"FACTS:\n{facts}"}]})
    r.raise_for_status()
    return _parse(r.json()["choices"][0]["message"]["content"])


def analyze(a: dict, ctx: dict) -> dict:
    s = get_settings()
    base = rules_analysis(a, ctx)
    provider = s.ai_provider.lower()
    try:
        if provider == "anthropic" and s.anthropic_api_key:
            out = _anthropic(_facts(a, ctx))
        elif provider == "openai" and s.openai_api_key:
            out = _openai(_facts(a, ctx))
        else:
            return base
        if out:
            return {"engine": provider, "sections": out, "titles": base["titles"], "disclaimer": base["disclaimer"]}
        log.warning("LLM output rejected or unparsable; using rules engine")
    except Exception as e:
        log.warning("LLM call failed (%s); using rules engine", e)
    base["engine"] = "rules (LLM fallback)"
    return base
