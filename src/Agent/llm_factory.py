"""
Shared LLM factory for agent orchestrator and subagents.

Keeps model/provider selection centralized and environment-driven to avoid
hardcoded values spread across files.
"""

from __future__ import annotations

import os
from typing import Any

from langchain.chat_models import init_chat_model
from langchain_anthropic import ChatAnthropic


def _resolve_default_model_name() -> str:
    return (
        os.getenv("OPENSENTINEL_MODEL_NAME")
        or os.getenv("ANTHROPIC_DEFAULT_MODEL")
        or os.getenv("OPENAI_DEFAULT_MODEL")
        or os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
        or os.getenv("GOOGLE_DEFAULT_MODEL")
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
    selected_model = model_name or DEFAULT_MODEL_NAME
    selected_temperature = DEFAULT_TEMPERATURE if temperature is None else temperature
    selected_max_tokens = DEFAULT_MAX_TOKENS if max_tokens is None else max_tokens

    if not selected_model:
        raise RuntimeError(
            "No default model configured. Set OPENSENTINEL_MODEL_NAME "
            "or provider default model environment variables."
        )

    try:
        if selected_model.startswith("claude"):
            return ChatAnthropic(
                model=selected_model,
                temperature=selected_temperature,
                max_tokens=selected_max_tokens,
            )
        return init_chat_model(selected_model, temperature=selected_temperature)
    except Exception as exc:
        raise RuntimeError(f"Failed to initialize model {selected_model}: {exc}") from exc


def create_subagent_llm() -> Any:
    """
    Create an LLM for subagents.

    Uses dedicated subagent override if provided, otherwise falls back to the
    main model setting.
    """
    subagent_model = os.getenv("OPENSENTINEL_SUBAGENT_MODEL_NAME")
    return create_llm(model_name=subagent_model)
