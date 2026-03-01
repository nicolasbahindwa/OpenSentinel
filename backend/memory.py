from pathlib import Path
from typing import Callable

from deepagents.backends import CompositeBackend, FilesystemBackend, StateBackend, StoreBackend


def composite_backend(skills_dir: str | Path | None = None) -> Callable:
    """Build a backend factory with routed storage by path prefix.

    Routes:
    - `/skills/`   -> FilesystemBackend rooted at local `skills/`
    - `/memories/` -> StoreBackend (persistent in configured store)
    - `/workspace/` -> StoreBackend (persistent in configured store)
    - default      -> StateBackend (ephemeral)
    """

    if skills_dir is None:
        resolved_skills_dir = Path(__file__).parent.parent / "skills"
    else:
        resolved_skills_dir = Path(skills_dir)

    # Build once so FilesystemBackend initialization does not run inside async request paths.
    skills_backend = FilesystemBackend(
        root_dir=str(resolved_skills_dir),
        virtual_mode=True,
    )

    def factory(runtime):
        routes = {
            "/memories/": StoreBackend(runtime, namespace=lambda ctx: ("memories",)),
            "/workspace/": StoreBackend(runtime, namespace=lambda ctx: ("workspace",)),
            "/skills/": skills_backend,
        }

        return CompositeBackend(
            default=StateBackend(runtime),
            routes=routes,
        )

    return factory
