"""
Configuration for OpenSentinel Agent
"""
import os
from typing import Any, Optional
from dataclasses import dataclass
from dotenv import load_dotenv
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from agent.prompt.system_prompt import SYSTEM_PROMPT

# Load environment variables
load_dotenv()


@dataclass
class Config:
    """Agent configuration"""
    base_model: Any
    subagent_model: Any
    base_agent_prompt: str = "You are a helpful AI assistant."
    tavily_api_key: Optional[str] = None
    nvidia_api_key: Optional[str] = None

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

        model_name = os.getenv("OPENSENTINEL_MODEL_NAME", "qwen/qwen3.5-397b-a17b")
        subagent_model_name = os.getenv("OPENSENTINEL_SUBAGENT_MODEL_NAME")
        model_temperature = float(os.getenv("OPENSENTINEL_MODEL_TEMPERATURE", "0.5"))
        model_max_tokens = int(os.getenv("OPENSENTINEL_MODEL_MAX_TOKENS", "4096"))

        # Create the base model with higher temperature for better tool usage
        base_model = ChatNVIDIA(
            model=model_name,
            temperature=model_temperature,
            max_tokens=model_max_tokens,
        )

        # Optional dedicated model for subagents; defaults to base model
        subagent_model = (
            ChatNVIDIA(
                model=subagent_model_name,
                temperature=model_temperature,
                max_tokens=model_max_tokens,
            )
            if subagent_model_name
            else base_model
        )
        # Load system prompt from prompt.py
        system_prompt = SYSTEM_PROMPT

        return cls(
            base_model=base_model,
            subagent_model=subagent_model,
            base_agent_prompt=system_prompt,
            tavily_api_key=tavily_api_key,
            nvidia_api_key=nvidia_api_key,
        )


__all__ = ["Config"]
