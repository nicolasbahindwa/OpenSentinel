"""
Configuration for OpenSentinel Agent
"""
import os
import tempfile
from typing import Any, Optional
from dataclasses import dataclass
from dotenv import load_dotenv
from langchain_nvidia_ai_endpoints import ChatNVIDIA

# Load environment variables
load_dotenv()


@dataclass
class Config:
    """Agent configuration"""
    base_model: Any
    subagent_model: Any
    judge_model: Any = None
    tavily_api_key: Optional[str] = None
    nvidia_api_key: Optional[str] = None
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

        base_model = ChatNVIDIA(
            model=model_name,
            temperature=model_temperature,
            max_completion_tokens=model_max_tokens,
            timeout=model_timeout,
        )

        # Optional dedicated model for subagents; defaults to base model
        subagent_model = (
            ChatNVIDIA(
                model=subagent_model_name,
                temperature=model_temperature,
                max_completion_tokens=model_max_tokens,
                timeout=model_timeout,
            )
            if subagent_model_name
            else base_model
        )

        # Lightweight judge model for guardrails semantic analysis
        judge_model_name = os.getenv("OPENSENTINEL_JUDGE_MODEL_NAME")
        judge_timeout = int(os.getenv("OPENSENTINEL_JUDGE_TIMEOUT", "15"))
        judge_model = (
            ChatNVIDIA(
                model=judge_model_name or model_name,
                temperature=0.0,
                max_completion_tokens=64,
                timeout=judge_timeout,
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
            workspace_dir=workspace_dir,
            sandbox_timeout_ms=sandbox_timeout_ms,
            sandbox_max_output=sandbox_max_output,
            sandbox_debug=sandbox_debug,
        )


__all__ = ["Config"]
