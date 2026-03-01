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

    print("\n" + "🔧 " + "="*58)
    print("🔧 COMPOSITE BACKEND INITIALIZATION")
    print("🔧 " + "="*58)

    if skills_dir is None:
        resolved_skills_dir = Path(__file__).parent.parent / "skills"
        print("⚠️  No skills_dir provided, using fallback path")
        print(f"   __file__ = {__file__}")
        print(f"   .parent = {Path(__file__).parent}")
        print(f"   .parent.parent = {Path(__file__).parent.parent}")
        print(f"   Resolved: {resolved_skills_dir}")
    else:
        resolved_skills_dir = Path(skills_dir)
        print(f"✅ skills_dir explicitly provided: {skills_dir}")
        print(f"   Type: {type(skills_dir)}")
        print(f"   Resolved to Path: {resolved_skills_dir}")

    # Verify the skills directory exists and list contents
    print(f"\n📂 Directory Verification:")
    print(f"   Path: {resolved_skills_dir}")
    print(f"   Exists: {resolved_skills_dir.exists()}")
    print(f"   Is absolute: {resolved_skills_dir.is_absolute()}")

    if resolved_skills_dir.exists():
        try:
            skills_found = list(resolved_skills_dir.iterdir())
            print(f"   Contents ({len(skills_found)} items): {[f.name for f in skills_found]}")

            # Check for SKILL.md files
            for item in skills_found:
                if item.is_dir():
                    skill_md = item / "SKILL.md"
                    if skill_md.exists():
                        print(f"      ✓ {item.name}/SKILL.md found ({skill_md.stat().st_size} bytes)")
                    else:
                        print(f"      ✗ {item.name}/SKILL.md NOT found")
        except Exception as e:
            print(f"   ⚠️ Error reading directory: {e}")
    else:
        print(f"   ❌ Directory does not exist!")

    # Build once so FilesystemBackend initialization does not run inside async request paths.
    print(f"\n📁 Creating FilesystemBackend:")
    print(f"   root_dir: {resolved_skills_dir}")
    print(f"   virtual_mode: True")

    try:
        skills_backend = FilesystemBackend(
            root_dir=str(resolved_skills_dir),
            virtual_mode=True,
        )
        print(f"   ✅ FilesystemBackend created successfully!")
    except Exception as e:
        print(f"   ❌ FilesystemBackend creation failed: {e}")
        raise

    def factory(runtime):
        print(f"\n🏭 Backend factory called with runtime: {runtime}")
        routes = {
            "/memories/": StoreBackend(runtime, namespace=lambda ctx: ("memories",)),
            "/workspace/": StoreBackend(runtime, namespace=lambda ctx: ("workspace",)),
            "/skills/": skills_backend,  # FilesystemBackend for skills
        }
        print(f"   Routes configured:")
        print(f"      /memories/  → StoreBackend")
        print(f"      /workspace/ → StoreBackend")
        print(f"      /skills/    → FilesystemBackend ({resolved_skills_dir})")
        print(f"      (default)   → StateBackend")

        composite = CompositeBackend(
            default=StateBackend(runtime),
            routes=routes,
        )
        print(f"   ✅ CompositeBackend instance created")
        return composite

    print("🔧 " + "="*58)
    print("✅ Returning backend factory function")
    print("🔧 " + "="*58 + "\n")

    return factory
