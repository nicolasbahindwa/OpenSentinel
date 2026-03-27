"""
Configuration for OpenSentinel Agent
"""
import os
import tempfile
import warnings
from collections.abc import Callable, Sequence
from typing import Any, Optional
from dataclasses import dataclass
from dotenv import load_dotenv
from langchain.chat_models.base import init_chat_model
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_core.tools import BaseTool

# Load environment variables
load_dotenv()

DEFAULT_TOOL_MODEL = "qwen/qwen3.5-122b-a10b"
DEFAULT_MODEL_PROVIDER = "nvidia"


def _parallel_tool_calls_enabled() -> bool:
    value = os.getenv("OPENSENTINEL_PARALLEL_TOOL_CALLS", "false").strip().lower()
    return value in {"1", "true", "yes", "on"}


class OpenSentinelChatNVIDIA(ChatNVIDIA):
    """ChatNVIDIA wrapper that enforces the repo's default tool-call policy at bind time."""

    def bind_tools(
        self,
        tools: Sequence[dict[str, Any] | type | Callable | BaseTool],
        *,
        tool_choice: Any | None = None,
        **kwargs: Any,
    ) -> Any:
        kwargs.setdefault("parallel_tool_calls", _parallel_tool_calls_enabled())
        return super().bind_tools(tools, tool_choice=tool_choice, **kwargs)


def _parse_model_spec(model_spec: str, default_provider: str = DEFAULT_MODEL_PROVIDER) -> tuple[str, str]:
    normalized = model_spec.strip()
    if ":" in normalized:
        provider, model_name = normalized.split(":", 1)
        return provider.strip().lower(), model_name.strip()
    return default_provider, normalized


def _provider_model_kwargs(
    *,
    provider: str,
    model_name: str,
    temperature: float,
    max_completion_tokens: int,
    timeout: int,
) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "model": model_name,
        "temperature": temperature,
        "timeout": timeout,
    }

    if provider in {"nvidia", "openai", "anthropic"}:
        kwargs["max_completion_tokens"] = max_completion_tokens
    else:
        kwargs["max_tokens"] = max_completion_tokens

    return kwargs


def _build_chat_model(
    *,
    provider: str,
    model_name: str,
    temperature: float,
    max_completion_tokens: int,
    timeout: int,
) -> BaseChatModel:
    kwargs = _provider_model_kwargs(
        provider=provider,
        model_name=model_name,
        temperature=temperature,
        max_completion_tokens=max_completion_tokens,
        timeout=timeout,
    )

    if provider == "nvidia":
        return OpenSentinelChatNVIDIA(**kwargs)

    return init_chat_model(model=model_name, model_provider=provider, **kwargs)


def _build_nvidia_model(
    *,
    model_name: str,
    temperature: float,
    max_completion_tokens: int,
    timeout: int,
    require_tool_support: bool,
) -> BaseChatModel:
    """Create a chat model and fall back if the selected model lacks tool support."""
    provider, resolved_model_name = _parse_model_spec(model_name)
    model = _build_chat_model(
        provider=provider,
        model_name=resolved_model_name,
        temperature=temperature,
        max_completion_tokens=max_completion_tokens,
        timeout=timeout,
    )

    if not require_tool_support:
        return model

    # NVIDIA exposes explicit supports_tools metadata. Other providers often do not.
    profile = getattr(getattr(model, "_client", None), "model", None)
    supports_tools = getattr(profile, "supports_tools", None)
    if provider != "nvidia" or supports_tools is not False:
        return model

    fallback_model = os.getenv("OPENSENTINEL_FALLBACK_MODEL", DEFAULT_TOOL_MODEL).strip() or DEFAULT_TOOL_MODEL
    if fallback_model == model_name:
        raise ValueError(
            f"Configured model '{model_name}' does not support tools. "
            "Set OPENSENTINEL_MODEL_NAME to a tool-capable model."
        )

    warnings.warn(
        f"Configured model '{model_name}' is not known to support tools. "
        f"Falling back to '{fallback_model}' for the agent model."
    )
    fallback_provider, fallback_model_name = _parse_model_spec(fallback_model)
    return _build_chat_model(
        provider=fallback_provider,
        model_name=fallback_model_name,
        temperature=temperature,
        max_completion_tokens=max_completion_tokens,
        timeout=timeout,
    )


@dataclass
class Config:
    """Agent configuration"""
    base_model: Any
    subagent_model: Any
    judge_model: Any = None
    tavily_api_key: Optional[str] = None
    nvidia_api_key: Optional[str] = None
    recursion_limit: int = 100  # Increased from 60 to handle complex multi-part queries
    provider_retry_attempts: int = 3
    provider_retry_base_delay_seconds: float = 1.0
    # Sandbox
    workspace_dir: str = ""
    sandbox_timeout_ms: int = 60_000
    sandbox_max_output: int = 50_000
    sandbox_debug: bool = False

    @classmethod
    def from_runnable_config(cls, config: Optional[dict] = None) -> "Config":
        """
        Load configuration from environment and runnable config.

        Args:
            config: Optional LangGraph runnable config

        Returns:
            Config instance
        """
        # Load API keys from environment
        tavily_api_key = os.getenv("TAVILY_API_KEY")
        nvidia_api_key = os.getenv("NVIDIA_API_KEY")

        model_name = os.getenv("OPENSENTINEL_MODEL_NAME", "qwen/qwen3.5-122b-a10b")
        subagent_model_name = os.getenv("OPENSENTINEL_SUBAGENT_MODEL_NAME")
        model_temperature = float(os.getenv("OPENSENTINEL_MODEL_TEMPERATURE", "0.5"))
        model_max_tokens = int(os.getenv("OPENSENTINEL_MODEL_MAX_TOKENS", "4096"))
        model_timeout = int(os.getenv("OPENSENTINEL_MODEL_TIMEOUT", "120"))
        recursion_limit = int(os.getenv("OPENSENTINEL_RECURSION_LIMIT", "100"))  # Default increased to 100
        provider_retry_attempts = int(os.getenv("OPENSENTINEL_PROVIDER_RETRY_ATTEMPTS", "3"))
        provider_retry_base_delay_seconds = float(
            os.getenv("OPENSENTINEL_PROVIDER_RETRY_BASE_DELAY_SECONDS", "1.0")
        )

        base_model = _build_nvidia_model(
            model_name=model_name,
            temperature=model_temperature,
            max_completion_tokens=model_max_tokens,
            timeout=model_timeout,
            require_tool_support=True,
        )

        # Optional dedicated model for subagents; defaults to base model
        subagent_model = (
            _build_nvidia_model(
                model_name=subagent_model_name,
                temperature=model_temperature,
                max_completion_tokens=model_max_tokens,
                timeout=model_timeout,
                require_tool_support=True,
            )
            if subagent_model_name
            else base_model
        )

        # Lightweight judge model for guardrails semantic analysis
        judge_model_name = os.getenv("OPENSENTINEL_JUDGE_MODEL_NAME")
        judge_timeout = int(os.getenv("OPENSENTINEL_JUDGE_TIMEOUT", "15"))
        judge_model = (
            _build_nvidia_model(
                model_name=judge_model_name or model_name,
                temperature=0.0,
                max_completion_tokens=64,
                timeout=judge_timeout,
                require_tool_support=False,
            )
            if os.getenv("OPENSENTINEL_ENABLE_JUDGE", "true").lower() == "true"
            else None
        )

        # Sandbox configuration
        workspace_dir = os.getenv(
            "OPENSENTINEL_WORKSPACE_DIR",
            os.path.join(tempfile.gettempdir(), "opensentinel_workspace"),
        )
        sandbox_timeout_ms = int(os.getenv("OPENSENTINEL_SANDBOX_TIMEOUT", "60000"))
        sandbox_max_output = int(os.getenv("OPENSENTINEL_SANDBOX_MAX_OUTPUT", "50000"))
        sandbox_debug = os.getenv("OPENSENTINEL_SANDBOX_DEBUG", "false").lower() == "true"

        return cls(
            base_model=base_model,
            subagent_model=subagent_model,
            judge_model=judge_model,
            tavily_api_key=tavily_api_key,
            nvidia_api_key=nvidia_api_key,
            recursion_limit=max(5, recursion_limit),
            provider_retry_attempts=max(1, provider_retry_attempts),
            provider_retry_base_delay_seconds=max(0.1, provider_retry_base_delay_seconds),
            workspace_dir=workspace_dir,
            sandbox_timeout_ms=sandbox_timeout_ms,
            sandbox_max_output=sandbox_max_output,
            sandbox_debug=sandbox_debug,
        )


__all__ = ["Config"]
