"""Gateway configuration — reads from environment variables with defaults."""

import os

DEFAULT_URL = "http://localhost:2024"
DEFAULT_ASSISTANT_ID = "agent"
DEFAULT_TIMEOUT = 120.0


class GatewayConfig:
    """Settings for the CLI gateway."""

    def __init__(self) -> None:
        self.url: str = os.getenv("LANGGRAPH_GATEWAY_URL", DEFAULT_URL)
        self.assistant_id: str = os.getenv("LANGGRAPH_ASSISTANT_ID", DEFAULT_ASSISTANT_ID)
        self.timeout: float = float(os.getenv("LANGGRAPH_GATEWAY_TIMEOUT", str(DEFAULT_TIMEOUT)))
