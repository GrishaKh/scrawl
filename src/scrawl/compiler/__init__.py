"""ScratchText compiler — text-based language that compiles to Scratch 3.0 block JSON.

Usage:
    from scrawl.compiler import compile_script

    blocks = compile_script(source_text, target_dict, project=proj)
"""

from __future__ import annotations

from typing import Any, Optional

from scrawl.compiler.codegen import CodeGenerator
from scrawl.compiler.errors import CompileError
from scrawl.compiler.lexer import Lexer
from scrawl.compiler.parser import Parser
from scrawl.compiler.registry import BlockRegistry
from scrawl.compiler.registry_data import ALL_BLOCKS
from scrawl.model import ScratchProject

__all__ = ["compile_script", "CompileError"]


def _load_default_registry() -> BlockRegistry:
    """Load the default block registry with all known blocks."""
    registry = BlockRegistry()
    registry.register_all(ALL_BLOCKS)
    return registry


# Module-level singleton (loaded lazily on first use)
_registry: Optional[BlockRegistry] = None


def _get_registry() -> BlockRegistry:
    global _registry
    if _registry is None:
        _registry = _load_default_registry()
    return _registry


def compile_script(
    source: str,
    target: dict[str, Any],
    project: Optional[ScratchProject] = None,
) -> dict[str, dict[str, Any]]:
    """Compile ScratchText source into block JSON and inject into target.

    Args:
        source: ScratchText source code.
        target: The target dict (sprite or stage) to inject blocks into.
        project: Optional full project for global variable/broadcast resolution.

    Returns:
        The generated blocks dict (also merged into target["blocks"]).

    Raises:
        CompileError: If the source cannot be compiled.
    """
    registry = _get_registry()
    tokens = Lexer(source).tokenize()
    scripts = Parser(tokens, registry).parse()
    gen = CodeGenerator(target, project)
    blocks = gen.generate(scripts)
    target.setdefault("blocks", {}).update(blocks)
    return blocks
