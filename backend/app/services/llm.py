"""Optional LLM access for Phase 9.

Deliberately tiny: one function that returns parsed JSON or ``None``. Callers
always have a rule-based fallback, so a missing key, a provider outage or a
malformed reply degrades quality instead of breaking the endpoint.

``LLM_MODEL`` uses ``provider:model`` (default ``groq:llama-3.3-70b-versatile``).
Groq exposes an OpenAI-compatible API, so the same client serves both providers.
"""

from __future__ import annotations

import json
import logging
import os
import re

from app.core.config import get_settings

log = logging.getLogger("app.llm")

_BASE_URLS = {"groq": "https://api.groq.com/openai/v1", "openai": None}


def _provider_and_model() -> tuple[str, str]:
    raw = get_settings().llm_model
    if ":" in raw:
        provider, model = raw.split(":", 1)
        return provider.lower(), model
    return "openai", raw


def _api_key(provider: str) -> str:
    s = get_settings()
    if provider == "groq":
        return s.groq_api_key or os.getenv("GROQ_API_KEY", "")
    return s.openai_api_key or os.getenv("OPENAI_API_KEY", "")


def is_configured() -> bool:
    s = get_settings()
    if not s.interview_use_llm:
        return False
    provider, _ = _provider_and_model()
    return provider in _BASE_URLS and bool(_api_key(provider))


def _extract_json(text: str) -> dict | None:
    text = (text or "").strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if fenced:
        text = fenced.group(1).strip()
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end <= start:
            return None
        try:
            value = json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return None
    return value if isinstance(value, dict) else None


def complete_json(system: str, user: str, max_tokens: int = 1800) -> dict | None:
    """Ask the model for a JSON object. Returns None when unconfigured or on any failure."""
    if not is_configured():
        return None
    provider, model = _provider_and_model()
    try:
        from openai import OpenAI

        client = OpenAI(
            api_key=_api_key(provider),
            base_url=_BASE_URLS[provider],
            timeout=get_settings().llm_timeout_seconds,
        )
        response = client.chat.completions.create(
            model=model,
            temperature=0.3,
            max_tokens=max_tokens,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        )
        return _extract_json(response.choices[0].message.content or "")
    except Exception:  # noqa: BLE001 - provider errors must never break the request
        log.warning("llm call failed; falling back to rule-based output", exc_info=True)
        return None
