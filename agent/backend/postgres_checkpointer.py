import os
from dataclasses import dataclass
from typing import Any
from dotenv import load_dotenv


@dataclass(frozen=True)
class PostgresCheckpointConfig:
    """Configuration for optional Postgres-backed LangGraph checkpointing."""

    enabled: bool
    database_url: str | None
    autocommit: bool

    @classmethod
    def from_env(cls) -> "PostgresCheckpointConfig":
        load_dotenv()
        enabled = os.getenv("LANGGRAPH_CHECKPOINT_ENABLED", "false").lower() == "true"
        database_url = os.getenv("LANGGRAPH_CHECKPOINT_DATABASE_URL")
        autocommit = os.getenv("LANGGRAPH_CHECKPOINT_AUTOCOMMIT", "true").lower() == "true"
        return cls(enabled=enabled, database_url=database_url, autocommit=autocommit)


@dataclass
class PostgresCheckpointerResources:
    """Holds the live DB connection and checkpointer instance."""

    connection: Any
    checkpointer: Any

    def close(self) -> None:
        self.connection.close()


def create_postgres_checkpointer(config: PostgresCheckpointConfig) -> PostgresCheckpointerResources:
    """Create Postgres checkpointer resources from explicit config.

    This does not attach the checkpointer to any graph. It only prepares resources.
    """
    if not config.enabled:
        raise ValueError("Postgres checkpointing is disabled (LANGGRAPH_CHECKPOINT_ENABLED=false).")
    if not config.database_url:
        raise ValueError("LANGGRAPH_CHECKPOINT_DATABASE_URL is required when checkpointing is enabled.")
    try:
        import psycopg
        from langgraph.checkpoint.postgres import PostgresSaver
        from psycopg.rows import dict_row
    except ImportError as exc:
        raise ImportError(
            "Postgres checkpoint dependencies are missing. Install `psycopg[binary,pool]` "
            "and `langgraph-checkpoint-postgres`."
        ) from exc

    conn = psycopg.connect(
        config.database_url,
        autocommit=config.autocommit,
        row_factory=dict_row,
    )
    checkpointer = PostgresSaver(conn)
    return PostgresCheckpointerResources(connection=conn, checkpointer=checkpointer)


def create_postgres_checkpointer_from_env() -> PostgresCheckpointerResources:
    """Create Postgres checkpointer resources from environment variables."""
    return create_postgres_checkpointer(PostgresCheckpointConfig.from_env())
