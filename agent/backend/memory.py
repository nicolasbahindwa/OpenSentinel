
import os

from deepagents.backends import (
    CompositeBackend,
    StateBackend,
    FilesystemBackend,
    StoreBackend,
)

from agent.config import Config
from agent.logger import get_logger
from agent.sandbox import create_local_sandbox

logger = get_logger("agent.backend", component="backend")


def composite_backend():
    base_dir = os.path.dirname(os.path.dirname(__file__))
    skills_dir = os.path.abspath(os.path.join(base_dir, "skills"))
    capabilities_dir = os.path.abspath(os.path.join(base_dir, "capabilities"))

    logger.info(
        "composite_backend_init",
        skills_dir=skills_dir,
        capabilities_dir=capabilities_dir,
    )

    # Sandbox is created lazily on first factory call to avoid
    # blocking I/O (Path.mkdir, Semaphore) at import time in the ASGI loop.
    _sandbox = None

    def _get_sandbox():
        nonlocal _sandbox
        if _sandbox is None:
            cfg = Config.from_runnable_config()
            logger.info(
                "sandbox_creating",
                workspace=cfg.workspace_dir,
                timeout_ms=cfg.sandbox_timeout_ms,
                max_output=cfg.sandbox_max_output,
                debug=cfg.sandbox_debug,
            )
            _sandbox = create_local_sandbox(
                workspace=cfg.workspace_dir,
                path_mappings={
                    "/skills/": skills_dir + os.sep,
                    "/workspace/": cfg.workspace_dir + os.sep,
                },
                timeout_ms=cfg.sandbox_timeout_ms,
                max_output_size=cfg.sandbox_max_output,
                debug=cfg.sandbox_debug,
            )
            logger.info("sandbox_created", sandbox_id=_sandbox.id)
        return _sandbox

    def factory(runtime):
        sandbox = _get_sandbox()
        routes = {
            "/memories/": StoreBackend(runtime),
            "/workspace/": sandbox,
            "/skills/": FilesystemBackend(
                root_dir=skills_dir,
                virtual_mode=True,
            ),
            "/capabilities/": FilesystemBackend(
                root_dir=capabilities_dir,
                virtual_mode=True,
            ),
        }

        logger.info(
            "composite_backend_ready",
            routes=list(routes.keys()),
            sandbox_id=sandbox.id,
            sandbox_workspace=sandbox.get_workspace(),
            sandbox_allowlist_enabled=sandbox.allowed_commands is not None,
        )

        return CompositeBackend(
            default=StateBackend(runtime),
            routes=routes,
        )

    return factory
