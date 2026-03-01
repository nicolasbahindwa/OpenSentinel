from typing import Callable

from deepagents.backends import CompositeBackend, FilesystemBackend, StateBackend, StoreBackend


def composite_backend(skills_dir: str = "skills") -> Callable:
    """Build a backend factory with routed storage by path prefix.

    Routes:
    - `/skills/`   -> FilesystemBackend rooted at skills directory
    - `/memories/` -> StoreBackend (persistent in configured store)
    - `/workspace/` -> StoreBackend (persistent in configured store)
    - default      -> StateBackend (ephemeral)

    Args:
        skills_dir: Path to skills directory (relative or absolute)
    """

    def factory(runtime):
        routes = {
            "/memories/": StoreBackend(runtime, namespace=lambda _: ("memories",)),
            "/workspace/": StoreBackend(runtime, namespace=lambda _: ("workspace",)),
            "/skills/": FilesystemBackend(
                root_dir=skills_dir,
                virtual_mode=True,
            ),
        }

        return CompositeBackend(
            default=StateBackend(runtime),
            routes=routes,
        )

    return factory