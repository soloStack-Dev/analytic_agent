from __future__ import annotations

import json
import re

import httpx

from ..config import (
    LLM_API_KEY,
    LLM_BASE_URL,
    LLM_MODEL,
    LLM_PROVIDER,
    LLM_TEMPERATURE,
    LLM_TIMEOUT,
)

# Providers use the same OpenAI-compatible request shape but different base URLs.
DEFAULT_BASES = {
    "openai": "https://api.openai.com/v1",
    "ollama": "http://localhost:11434/v1",
    "groq": "https://api.groq.com/openai/v1",
    "openrouter": "https://openrouter.ai/api/v1",
    "deepseek": "https://api.deepseek.com/v1",
}


class LLMError(Exception):
    pass


def _endpoint() -> str:
    """Build the provider endpoint while allowing a custom compatible base URL."""
    base = LLM_BASE_URL or DEFAULT_BASES.get(
        LLM_PROVIDER, DEFAULT_BASES["openai"]
    )
    return base.rstrip("/") + "/chat/completions"


def extract_json(text: str) -> dict:
    """Parse a JSON object from plain output or a fenced markdown response."""
    cleaned = re.sub(r"^```(?:json)?\s*", "", text.strip())
    cleaned = re.sub(r"\s*```$", "", cleaned).strip()
    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass
    # Some models add a short explanation before the JSON; isolate its outer object.
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end > start:
        return json.loads(cleaned[start : end + 1])
    raise LLMError("LLM returned non-JSON output")


def is_configured() -> bool:
    """Report whether the planner can make an authenticated model request."""
    return bool(LLM_API_KEY) and bool(LLM_MODEL or LLM_PROVIDER)


def call_llm_json(
    system: str,
    user: str,
    temperature: float | None = None,
    model: str | None = None,
) -> dict:
    """Call the configured provider and return its validated JSON object."""
    if not LLM_API_KEY:
        raise LLMError("LLM_API_KEY is not configured in .env")
    if not LLM_MODEL and not model:
        raise LLMError("LLM_MODEL is not configured in .env")

    payload = {
        "model": model or LLM_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": LLM_TEMPERATURE if temperature is None else temperature,
        "stream": False,
    }
    headers = {"Content-Type": "application/json"}
    if LLM_API_KEY:
        headers["Authorization"] = f"Bearer {LLM_API_KEY}"

    # Use a non-streaming request because planning and explanation both need one
    # complete JSON document before the graph can continue.
    try:
        with httpx.Client(timeout=LLM_TIMEOUT) as client:
            response = client.post(_endpoint(), json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text[:300] if exc.response is not None else ""
        raise LLMError(
            f"LLM provider returned HTTP {exc.response.status_code}: {detail}"
        ) from exc
    except httpx.RequestError as exc:
        raise LLMError(f"LLM provider unreachable: {exc}") from exc

    # OpenAI-compatible providers place the model response at this stable path.
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMError("LLM response missing message content") from exc

    return extract_json(content)