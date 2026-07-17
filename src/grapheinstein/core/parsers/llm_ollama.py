"""Ollama local HTTP client for LLM enrichment (stdlib urllib)."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Callable

from loguru import logger

DEFAULT_BASE_URL = "http://localhost:11434"
DEFAULT_MODEL = "qwen3.5-2b-mlx:fp16-8gbGPU"

ENRICH_FORMAT: dict[str, Any] = {
    "type": "object",
    "properties": {
        "entities": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "kind": {"type": "string"},
                    "evidence": {"type": "string"},
                    "confidence": {"type": "number"},
                },
                "required": ["name", "evidence", "confidence"],
            },
        },
        "relations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "type": {"type": "string"},
                    "subject": {"type": "string"},
                    "object": {"type": "string"},
                    "evidence": {"type": "string"},
                    "confidence": {"type": "number"},
                },
                "required": ["type", "subject", "object", "evidence", "confidence"],
            },
        },
    },
    "required": ["entities", "relations"],
}

SYSTEM_PROMPT = (
    "You extract domain concepts and relations from a source file chunk. "
    "Return JSON only matching the schema. "
    "entities: domain terms or libraries mentioned in the text. "
    "relations: implements (code symbol implements a concept), "
    "depends_on (file/code depends on a library concept), "
    "or mentions (text mentions a concept). "
    "evidence must be a short verbatim snippet from the chunk. "
    "confidence is 0.0-1.0."
)


class OllamaError(Exception):
    """Raised when Ollama HTTP calls fail."""


def _request_json(
    method: str,
    url: str,
    *,
    body: dict[str, Any] | None = None,
    timeout: float = 120.0,
) -> Any:
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace") if exc.fp else str(exc)
        raise OllamaError(f"Ollama HTTP {exc.code} for {url}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise OllamaError(f"Ollama unreachable at {url}: {exc.reason}") from exc
    except TimeoutError as exc:
        raise OllamaError(f"Ollama timeout for {url}") from exc
    try:
        return json.loads(raw) if raw else {}
    except json.JSONDecodeError as exc:
        raise OllamaError(f"Invalid JSON from Ollama at {url}: {exc}") from exc


def list_models(base_url: str = DEFAULT_BASE_URL, *, timeout: float = 10.0) -> list[str]:
    """Return model names/tags available on the local Ollama instance."""
    url = base_url.rstrip("/") + "/api/tags"
    payload = _request_json("GET", url, timeout=timeout)
    models = payload.get("models") if isinstance(payload, dict) else None
    if not isinstance(models, list):
        return []
    names: list[str] = []
    for item in models:
        if isinstance(item, dict):
            name = item.get("name") or item.get("model")
            if isinstance(name, str) and name.strip():
                names.append(name.strip())
    return names


def model_available(
    model: str,
    base_url: str = DEFAULT_BASE_URL,
    *,
    tags: list[str] | None = None,
    timeout: float = 10.0,
) -> bool:
    """True if model tag is present (exact or prefix before ':')."""
    available = tags if tags is not None else list_models(base_url, timeout=timeout)
    if model in available:
        return True
    # Accept short name match (model without tag matches tagged variants)
    base = model.split(":", 1)[0]
    for name in available:
        if name == model or name.split(":", 1)[0] == base or name.startswith(model + ":"):
            return True
    return False


def chat(
    *,
    model: str,
    user_content: str,
    base_url: str = DEFAULT_BASE_URL,
    system: str = SYSTEM_PROMPT,
    response_format: dict[str, Any] | None = None,
    timeout: float = 120.0,
) -> dict[str, Any]:
    """
    Call Ollama POST /api/chat with structured format.
    Returns parsed JSON object from assistant message content.
    """
    url = base_url.rstrip("/") + "/api/chat"
    body: dict[str, Any] = {
        "model": model,
        "stream": False,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user_content},
        ],
        "format": response_format if response_format is not None else ENRICH_FORMAT,
    }
    payload = _request_json("POST", url, body=body, timeout=timeout)
    if not isinstance(payload, dict):
        raise OllamaError("Ollama chat response was not an object")
    message = payload.get("message") or {}
    content = message.get("content") if isinstance(message, dict) else None
    if not isinstance(content, str) or not content.strip():
        raise OllamaError("Ollama chat returned empty message content")
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as exc:
        raise OllamaError(f"Ollama chat content was not valid JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise OllamaError("Ollama chat JSON root must be an object")
    return parsed


def check_ready(
    *,
    model: str,
    base_url: str = DEFAULT_BASE_URL,
    list_models_fn: Callable[[str], list[str]] | None = None,
) -> tuple[bool, str]:
    """
    Preflight: returns (ok, message).
    ok=False means enrichment should be skipped (warn and continue).
    """
    lister = list_models_fn or (lambda url: list_models(url))
    try:
        tags = lister(base_url)
    except OllamaError as exc:
        msg = f"LLM enrichment skipped: Ollama unreachable at {base_url} ({exc})"
        logger.warning(msg)
        return False, msg
    except Exception as exc:  # noqa: BLE001
        msg = f"LLM enrichment skipped: cannot list models at {base_url} ({exc})"
        logger.warning(msg)
        return False, msg
    if not model_available(model, base_url, tags=tags):
        msg = (
            f"LLM enrichment skipped: model {model!r} not found at {base_url}. "
            f"Available: {tags[:20] or '(none)'}. "
            "Configure --llm-model or install the model (e.g. ollama pull)."
        )
        logger.warning(msg)
        return False, msg
    return True, f"Using Ollama model {model} at {base_url}"


__all__ = [
    "DEFAULT_BASE_URL",
    "DEFAULT_MODEL",
    "ENRICH_FORMAT",
    "OllamaError",
    "SYSTEM_PROMPT",
    "chat",
    "check_ready",
    "list_models",
    "model_available",
]
