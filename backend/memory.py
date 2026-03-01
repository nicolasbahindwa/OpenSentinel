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
        print("#" * 50)
        print("No skills_dir provided, defaulting to:", resolved_skills_dir)
        print(f"  __file__ = {__file__}")
        print(f"  .parent = {Path(__file__).parent}")
        print(f"  .parent.parent = {Path(__file__).parent.parent}")
        print("#" * 50)
    else:
        resolved_skills_dir = Path(skills_dir)
        print("*" * 50)
        print("skills_dir explicitly provided:", resolved_skills_dir)
        print("*" * 50)

    # Verify the skills directory exists and list contents
    print(f"🔍 Resolved skills_dir: {resolved_skills_dir}")
    print(f"🔍 Skills directory exists: {resolved_skills_dir.exists()}")
    if resolved_skills_dir.exists():
        try:
            skills_found = list(resolved_skills_dir.iterdir())
            print(f"🔍 Contents: {[f.name for f in skills_found]}")
        except Exception as e:
            print(f"⚠️ Error reading skills directory: {e}")

    # Build once so FilesystemBackend initialization does not run inside async request paths.
    print(f"📁 Creating FilesystemBackend with root_dir={resolved_skills_dir}")
    skills_backend = FilesystemBackend(
        root_dir=str(resolved_skills_dir),
        virtual_mode=True,
    )
    print(f"✅ FilesystemBackend created successfully")

    def factory(runtime):
        routes = {
            "/memories/": StoreBackend(runtime, namespace=lambda ctx: ("memories",)),
            "/workspace/": StoreBackend(runtime, namespace=lambda ctx: ("workspace",)),
            "/skills/": skills_backend,  # FilesystemBackend for skills
        }

        return CompositeBackend(
            default=StateBackend(runtime),
            routes=routes,
        )

    return factory
