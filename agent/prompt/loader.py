"""Prompt loader for modular system prompts."""
from pathlib import Path
from functools import lru_cache
from typing import Optional


class PromptLoader:
    """Lazy loader for modular prompt components."""

    def __init__(self, modules_dir: Optional[Path] = None):
        if modules_dir is None:
            modules_dir = Path(__file__).parent / "modules"
        self.modules_dir = Path(modules_dir)

    @lru_cache(maxsize=32)
    def load_module(self, module_name: str) -> str:
        """
        Load a prompt module on-demand with caching.

        Args:
            module_name: Name of the module (without .md extension)

        Returns:
            Module content as string
        """
        module_path = self.modules_dir / f"{module_name}.md"

        if not module_path.exists():
            return f"# Module '{module_name}' not found"

        try:
            with open(module_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            return f"# Error loading module '{module_name}': {e}"

    def build_prompt(self, *modules: str, include_core: bool = True) -> str:
        """
        Build a prompt from specified modules.

        Args:
            *modules: Module names to include
            include_core: Whether to include core module (default: True)

        Returns:
            Combined prompt string
        """
        parts = []

        # Always include core unless explicitly disabled
        if include_core:
            parts.append(self.load_module("core"))

        # Load requested modules
        for module in modules:
            parts.append(self.load_module(module))

        return "\n\n---\n\n".join(parts)

    def get_minimal_prompt(self) -> str:
        """Get minimal prompt with just core identity."""
        return self.load_module("core")

    def get_tools_prompt(self) -> str:
        """Get prompt with core + tools guidance."""
        return self.build_prompt("tools")

    def get_full_prompt(self) -> str:
        """Get full prompt with all modules."""
        return self.build_prompt("safety", "tools", "skills", "subagents")


# Global instance for easy access
_loader = PromptLoader()


def get_prompt(*modules: str, include_core: bool = True) -> str:
    """
    Get a prompt with specified modules.

    Args:
        *modules: Module names to include
        include_core: Whether to include core module

    Returns:
        Combined prompt
    """
    return _loader.build_prompt(*modules, include_core=include_core)


def get_minimal_prompt() -> str:
    """Get minimal prompt - just core identity."""
    return _loader.get_minimal_prompt()


def get_tools_prompt() -> str:
    """Get prompt with tools guidance."""
    return _loader.get_tools_prompt()


def get_full_prompt() -> str:
    """Get full prompt with all modules."""
    return _loader.get_full_prompt()


__all__ = [
    "PromptLoader",
    "get_prompt",
    "get_minimal_prompt",
    "get_tools_prompt",
    "get_full_prompt",
]
