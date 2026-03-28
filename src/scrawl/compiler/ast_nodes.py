"""AST node definitions for the ScratchText compiler."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Input nodes — represent values flowing into a block's input slots
# ---------------------------------------------------------------------------


@dataclass
class InputNode:
    """Base class for all input values."""

    pass


@dataclass
class LiteralInput(InputNode):
    """A literal number or string value."""

    value: str
    input_type: str  # "number", "string", "positive_number", "positive_integer",
    #                  "integer", "angle", "color"


@dataclass
class VariableInput(InputNode):
    """A variable reference: (my variable)."""

    name: str


@dataclass
class ListInput(InputNode):
    """A list reference."""

    name: str


@dataclass
class BroadcastInput(InputNode):
    """A broadcast reference."""

    name: str


@dataclass
class ReporterInput(InputNode):
    """A nested reporter block used as an input value."""

    block: BlockNode


# ---------------------------------------------------------------------------
# Field nodes — represent dropdown/field selections
# ---------------------------------------------------------------------------


@dataclass
class FieldNode:
    """A field value (dropdown, variable name, etc.)."""

    value: str
    ref_id: Optional[str] = None  # Resolved during codegen


# ---------------------------------------------------------------------------
# Block and statement nodes
# ---------------------------------------------------------------------------


@dataclass
class BlockNode:
    """A single block invocation."""

    opcode: str
    inputs: dict[str, InputNode] = field(default_factory=dict)
    fields: dict[str, FieldNode] = field(default_factory=dict)
    line: int = 0
    mutation: Optional[dict] = None  # For procedures_call blocks


@dataclass
class StatementNode:
    """A statement: either a simple block or a C-block with body."""

    block: BlockNode
    substacks: list[list[StatementNode]] = field(default_factory=list)
    # C-blocks: substacks[0] = first body, substacks[1] = else body (if-else)


@dataclass
class ScriptNode:
    """A complete script (hat block + body statements)."""

    hat: BlockNode
    body: list[StatementNode] = field(default_factory=list)
    line: int = 0


@dataclass
class CustomBlockDef:
    """A custom block definition (define ... end)."""

    proccode: str  # e.g., "my block %s %s"
    argument_names: list[str] = field(default_factory=list)
    argument_types: list[str] = field(default_factory=list)  # "s" or "b"
    warp: bool = False
    body: list[StatementNode] = field(default_factory=list)
    line: int = 0
