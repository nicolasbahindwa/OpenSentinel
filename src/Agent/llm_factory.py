"""
Shared LLM factory for agent orchestrator and subagents.

Keeps model/provider selection centralized and environment-driven to avoid
hardcoded values spread across files.
"""

from __future__ import annotations

import os
from typing import Any, List, Tuple

from langchain.chat_models import init_chat_model
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_nvidia_ai_endpoints import ChatNVIDIA


def _split_model_candidates(model_spec: str) -> List[str]:
    """Allow comma-separated model specs: primary first, then fallbacks."""
    return [candidate.strip() for candidate in model_spec.split(",") if candidate.strip()]


def _parse_provider_model(model_spec: str) -> Tuple[str | None, str]:
    """
    Parse provider-qualified model strings like:
    - google_genai:gemini-2.0-flash
    - openai:gpt-4o-mini
    """
    if ":" in model_spec:
        provider, model = model_spec.split(":", 1)
        provider = provider.strip()
        model = model.strip()
        if provider and model:
            return provider, model
    return None, model_spec


def _create_single_model(model_spec: str, temperature: float, max_tokens: int) -> Any:
    """Create one concrete chat model from a model spec."""
    provider, model = _parse_provider_model(model_spec)

    if provider:
        return init_chat_model(
            model,
            model_provider=provider,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    if model.startswith("claude"):
        return ChatAnthropic(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    if model.startswith("google/") or model.startswith("gemini"):
        return ChatGoogleGenerativeAI(
            model=model.replace("google/", ""),
            temperature=temperature,
            max_tokens=max_tokens,
        )

    if model.startswith("nvidia/") or model.startswith("meta/") or model.startswith("mistralai/") or model.startswith("moonshotai/") or model.startswith("qwen/"):
        return ChatNVIDIA(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    # Default route for non-provider-qualified names.
    return init_chat_model(
        model,
        temperature=temperature,
        max_tokens=max_tokens,
        model_provider="openai",
    )


def _resolve_default_model_name() -> str:
    return (
        os.getenv("OPENSENTINEL_MODEL_NAME")
        or os.getenv("GOOGLE_DEFAULT_MODEL")
        or os.getenv("ANTHROPIC_DEFAULT_MODEL")
        or os.getenv("OPENAI_DEFAULT_MODEL")
        or os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
        or ""
    )


DEFAULT_MODEL_NAME = _resolve_default_model_name()
DEFAULT_TEMPERATURE = float(os.getenv("OPENSENTINEL_MODEL_TEMPERATURE", "0.3"))
DEFAULT_MAX_TOKENS = int(os.getenv("OPENSENTINEL_MODEL_MAX_TOKENS", "8192"))


def create_llm(
    model_name: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> Any:
    """Initialize and return a chat model instance."""
    selected_model_spec = model_name or DEFAULT_MODEL_NAME
    selected_temperature = DEFAULT_TEMPERATURE if temperature is None else temperature
    selected_max_tokens = DEFAULT_MAX_TOKENS if max_tokens is None else max_tokens

    if not selected_model_spec:
        raise RuntimeError(
            "No default model configured. Set OPENSENTINEL_MODEL_NAME "
            "or provider default model environment variables."
        )

    candidates = _split_model_candidates(selected_model_spec)
    primary = candidates[0]
    fallbacks = candidates[1:]

    # Explicit handling for this compatibility pair:
    # prefer google_genai:gemini-2.0-flash as execution primary, keep 1.5-flash
    # as fallback reference.
    if primary == "gemini-1.5-flash":
        preferred = os.getenv("OPENSENTINEL_FALLBACK_MODEL", "google_genai:gemini-2.0-flash")
        if preferred not in fallbacks:
            fallbacks.insert(0, preferred)
        primary, fallbacks = fallbacks[0], [candidate for candidate in fallbacks[1:] if candidate != primary] + ["gemini-1.5-flash"]

    try:
        primary_model = _create_single_model(primary, selected_temperature, selected_max_tokens)
        fallback_models = [
            _create_single_model(candidate, selected_temperature, selected_max_tokens)
            for candidate in fallbacks
        ]

        if fallback_models:
            return primary_model.with_fallbacks(fallback_models)
        return primary_model
    except Exception as exc:
        raise RuntimeError(f"Failed to initialize model chain '{selected_model_spec}': {exc}") from exc


def create_subagent_llm() -> Any:
    """
    Create an LLM for subagents.

    Uses dedicated subagent override if provided, otherwise falls back to the
    main model setting.
    """
    subagent_model = os.getenv("OPENSENTINEL_SUBAGENT_MODEL_NAME")
    return create_llm(model_name=subagent_model)
