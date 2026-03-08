
import os
from deepagents.backends import (
    CompositeBackend, 
    StateBackend, 
    FilesystemBackend, 
    StoreBackend
)

def composite_backend():
    base_dir = os.path.dirname(os.path.dirname(__file__))
    skills_dir = os.path.abspath(os.path.join(base_dir, "skills"))
    capabilities_dir = os.path.abspath(os.path.join(base_dir, "capabilities"))
        
    def factory(runtime):
        routes = {
            "/memories/": StoreBackend(runtime),
            "/workspace/": StoreBackend(runtime),
            "/skills/": FilesystemBackend(
                root_dir=skills_dir,
                virtual_mode=True,
            ),
            "/capabilities/": FilesystemBackend(
                root_dir=capabilities_dir,
                virtual_mode=True,
            ),
        }

        return CompositeBackend(
            default=StateBackend(runtime),
            routes=routes
        )

    return factory
