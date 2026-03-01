"""
Configuration for OpenSentinel Agent
"""
import os
from typing import Any, Optional
from dataclasses import dataclass
from dotenv import load_dotenv
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from prompt import SYSTEM_PROMPT

# Load environment variables
load_dotenv()


@dataclass
class Config:
    """Agent configuration"""
    base_model: Any
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

        # Create the base model with higher temperature for better tool usage
        base_model = ChatNVIDIA(
            model="qwen/qwen3.5-397b-a17b",
            temperature=0.5,  # Higher temp encourages tool usage
            max_tokens=4096,   # Increased for longer responses
        )
        # Load system prompt from prompt.py
        system_prompt = SYSTEM_PROMPT

        return cls(
            base_model=base_model,
            base_agent_prompt=system_prompt,
            tavily_api_key=tavily_api_key,
            nvidia_api_key=nvidia_api_key,
        )


__all__ = ["Config"]
