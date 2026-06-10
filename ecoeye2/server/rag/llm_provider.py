"""
LLM Provider abstraction for EcoEye2.

Supports multiple LLM backends (Google GenAI, Groq) behind a unified
interface.  The active provider is stored in-memory and can be switched
at runtime via the ``/api/v1/ai/provider`` endpoint.

Embeddings always go through Google GenAI regardless of the active LLM
provider because Groq does not offer an embedding API.
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Provider registry
# ---------------------------------------------------------------------------

PROVIDERS: dict[str, dict[str, Any]] = {
    "googlegenai": {
        "label": "Google GenAI (Gemini)",
        "model": "gemini-2.5-flash",
        "env_key": "GEMINI_API_KEY",
    },
    "groq": {
        "label": "Groq",
        "model": "llama-3.3-70b-versatile",
        "env_key": "GROQ_API_KEY",
    },
}

_active_provider: str = "googlegenai"


# ---------------------------------------------------------------------------
# Getters / setters
# ---------------------------------------------------------------------------

def get_active_provider() -> str:
    """Return the name of the currently active provider."""
    return _active_provider


def set_active_provider(name: str) -> None:
    """Set the active LLM provider (validates against PROVIDERS)."""
    global _active_provider
    if name not in PROVIDERS:
        raise ValueError(
            f"Unknown provider '{name}'. Choose from: {list(PROVIDERS.keys())}"
        )
    _active_provider = name
    logger.info("Active LLM provider set to '%s'", name)


def get_provider_status() -> dict[str, Any]:
    """Return current provider info + which API keys are configured."""
    items: list[dict[str, Any]] = []
    for key, meta in PROVIDERS.items():
        items.append(
            {
                "id": key,
                "label": meta["label"],
                "model": meta["model"],
                "api_key_set": bool(os.environ.get(meta["env_key"], "").strip()),
            }
        )
    return {
        "active": _active_provider,
        "providers": items,
    }


# ---------------------------------------------------------------------------
# Unified generation
# ---------------------------------------------------------------------------

def _resolve_api_key(provider: str, explicit_key: str | None = None) -> str:
    """Resolve the API key for *provider*, raising if missing."""
    if explicit_key:
        return explicit_key
    env_var = PROVIDERS[provider]["env_key"]
    key = os.environ.get(env_var, "").strip()
    if not key:
        raise RuntimeError(
            f"API key for provider '{provider}' is not set. "
            f"Please set the {env_var} environment variable."
        )
    return key


def generate_text(
    prompt: str,
    system_instruction: str,
    api_key: str | None = None,
    *,
    provider: str | None = None,
) -> str:
    """
    Generate text using the active (or specified) LLM provider.

    Parameters
    ----------
    prompt : str
        The user/content prompt.
    system_instruction : str
        System-level instruction for the model.
    api_key : str | None
        Explicit API key.  Resolved from env if ``None``.
    provider : str | None
        Override the active provider for this single call.

    Returns
    -------
    str
        The generated text response.
    """
    provider = provider or _active_provider
    meta = PROVIDERS.get(provider)
    if meta is None:
        raise ValueError(f"Unknown provider '{provider}'")

    key = _resolve_api_key(provider, api_key)

    if provider == "googlegenai":
        return _generate_googlegenai(prompt, system_instruction, key, meta["model"])
    elif provider == "groq":
        return _generate_groq(prompt, system_instruction, key, meta["model"])
    else:
        raise ValueError(f"No generation handler for provider '{provider}'")


# ---------------------------------------------------------------------------
# Provider-specific backends
# ---------------------------------------------------------------------------

def _generate_googlegenai(
    prompt: str, system_instruction: str, api_key: str, model: str
) -> str:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    
    try:
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
            ),
        )
        return response.text
    except Exception as e:
        logger.warning(
            "Primary Google GenAI model '%s' failed: %s. Trying fallback models...",
            model,
            e,
        )
        fallbacks = ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-2.5-pro", "gemini-1.5-pro"]
        fallbacks = [fb for fb in fallbacks if fb != model]
        
        for fb_model in fallbacks:
            try:
                logger.info("Attempting generation with fallback model: '%s'", fb_model)
                response = client.models.generate_content(
                    model=fb_model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                    ),
                )
                return response.text
            except Exception as fb_err:
                logger.warning(
                    "Fallback model '%s' failed: %s",
                    fb_model,
                    fb_err,
                )
        
        # If all fallbacks failed, raise the original exception
        raise e


def _generate_groq(
    prompt: str, system_instruction: str, api_key: str, model: str
) -> str:
    from groq import Groq

    client = Groq(api_key=api_key)
    completion = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": prompt},
        ],
        temperature=1,
        max_completion_tokens=8192,
        top_p=1,
        stream=True,
        stop=None,
    )

    # Collect streamed chunks into a single string
    parts: list[str] = []
    for chunk in completion:
        delta = chunk.choices[0].delta
        if delta and delta.content:
            parts.append(delta.content)
    return "".join(parts)
