"""Opcode registry — pattern compilation and matching engine.

Maps natural-language block patterns to Scratch opcode specifications.
Adding a new block = adding one BlockDef entry in registry_data.py.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Optional

from scrawl.compiler.tokens import Token, TokenType


# ---------------------------------------------------------------------------
# Block shape classification
# ---------------------------------------------------------------------------


class BlockShape(Enum):
    HAT = auto()       # Top-level event block (when flag clicked, etc.)
    STACK = auto()     # Normal statement block
    C_BLOCK = auto()   # Has SUBSTACK (forever, if, repeat, etc.)
    CAP = auto()       # Terminal block (stop all, delete this clone)
    REPORTER = auto()  # Returns a value (number/string)
    BOOLEAN = auto()   # Returns a boolean


# ---------------------------------------------------------------------------
# Input and field specifications
# ---------------------------------------------------------------------------


@dataclass
class InputSpec:
    """Specification for one input slot of a block."""

    name: str              # Scratch input key, e.g., "STEPS", "VALUE"
    type: str              # "number", "string", "positive_number", "positive_integer",
    #                        "integer", "angle", "color", "boolean"
    default: Optional[str] = None  # Default value for shadow
    primitive_code: Optional[int] = None  # 4=number, 5=pos_num, 6=pos_int, 7=int,
    #                                       8=angle, 9=color, 10=string


@dataclass
class FieldSpec:
    """Specification for one field of a block."""

    name: str       # Scratch field key, e.g., "VARIABLE", "BROADCAST_OPTION"
    field_type: str  # "variable", "list", "broadcast", "costume", "sound",
    #                  "backdrop", "key", "stop_option", "clone_option",
    #                  "touching_menu", "goto_menu", etc.
    default_value: Optional[str] = None  # Hardcoded value when not captured from pattern


@dataclass
class MenuSpec:
    """A menu shadow block (dropdown) that accompanies certain blocks."""

    opcode: str       # Shadow block opcode, e.g., "sensing_touchingobjectmenu"
    field_name: str   # Field name in the shadow, e.g., "TOUCHINGOBJECTMENU"
    input_name: str   # Input key on the parent block


# ---------------------------------------------------------------------------
# Block definition
# ---------------------------------------------------------------------------


@dataclass
class BlockDef:
    """Complete definition of one block pattern."""

    pattern: str        # e.g., "move (STEPS) steps"
    opcode: str         # e.g., "motion_movesteps"
    shape: BlockShape
    inputs: list[InputSpec] = field(default_factory=list)
    fields: list[FieldSpec] = field(default_factory=list)
    menu: Optional[MenuSpec] = None
    substacks: int = 0  # Number of substacks (0, 1, or 2 for if-else)
    has_next: bool = True  # False for cap blocks and reporters


# ---------------------------------------------------------------------------
# Pattern compilation
# ---------------------------------------------------------------------------


class PatternElementKind(Enum):
    LITERAL = auto()        # A fixed word to match
    PAREN_INPUT = auto()    # (NAME) — parenthesized input
    BRACKET_FIELD = auto()  # [NAME v] — bracketed dropdown field
    BRACKET_INPUT = auto()  # [NAME] — bracketed string input (no dropdown)
    ANGLE_INPUT = auto()    # <NAME> — boolean input


@dataclass
class PatternElement:
    """One element in a compiled pattern."""

    kind: PatternElementKind
    value: str  # For LITERAL: the word (lowercased). For inputs/fields: the name.


@dataclass
class CompiledPattern:
    """A pattern compiled into matchable elements."""

    elements: list[PatternElement]
    block_def: BlockDef
    first_word: Optional[str]  # First literal word (for indexing), or None


# Pattern element regex for parsing pattern strings
_PAREN_RE = re.compile(r"^\((\w+)\)$")
_BRACKET_V_RE = re.compile(r"^\[(\w+)\s+v\]$")
_BRACKET_RE = re.compile(r"^\[(\w+)\]$")
_ANGLE_RE = re.compile(r"^<(\w+)>$")


def compile_pattern(block_def: BlockDef) -> CompiledPattern:
    """Parse a pattern string into a list of matchable elements."""
    elements: list[PatternElement] = []
    first_word: Optional[str] = None

    # Tokenize the pattern string
    pattern = block_def.pattern
    i = 0
    while i < len(pattern):
        ch = pattern[i]

        # Skip whitespace
        if ch == " ":
            i += 1
            continue

        # Parenthesized input: (NAME)
        if ch == "(":
            j = pattern.index(")", i)
            name = pattern[i + 1 : j]
            elements.append(
                PatternElement(PatternElementKind.PAREN_INPUT, name)
            )
            i = j + 1
            continue

        # Bracketed: [NAME v] or [NAME]
        if ch == "[":
            j = pattern.index("]", i)
            inner = pattern[i + 1 : j]
            if inner.endswith(" v"):
                name = inner[:-2]
                elements.append(
                    PatternElement(PatternElementKind.BRACKET_FIELD, name)
                )
            else:
                elements.append(
                    PatternElement(PatternElementKind.BRACKET_INPUT, inner)
                )
            i = j + 1
            continue

        # Angle-bracketed: <NAME> — only if it matches the pattern <WORD>
        if ch == "<":
            close = pattern.find(">", i)
            if close != -1:
                inner = pattern[i + 1 : close]
                # It's a proper angle-bracket input if inner is a single identifier
                if inner.strip() and re.match(r"^\w+$", inner.strip()):
                    elements.append(
                        PatternElement(PatternElementKind.ANGLE_INPUT, inner.strip())
                    )
                    i = close + 1
                    continue
            # Otherwise treat < as a literal word
            elements.append(PatternElement(PatternElementKind.LITERAL, "<"))
            if first_word is None:
                first_word = "<"
            i += 1
            continue

        # > as a literal (for operator patterns like ">")
        if ch == ">":
            elements.append(PatternElement(PatternElementKind.LITERAL, ">"))
            if first_word is None:
                first_word = ">"
            i += 1
            continue

        # Word literal
        j = i
        while j < len(pattern) and pattern[j] not in " ([<>":
            j += 1
        word = pattern[i:j].lower()
        elements.append(PatternElement(PatternElementKind.LITERAL, word))
        if first_word is None:
            first_word = word
        i = j

    return CompiledPattern(
        elements=elements, block_def=block_def, first_word=first_word
    )


# ---------------------------------------------------------------------------
# Block registry
# ---------------------------------------------------------------------------


class BlockRegistry:
    """Registry of all known block patterns with fast matching."""

    def __init__(self) -> None:
        self._patterns: list[CompiledPattern] = []
        self._by_first_word: dict[str, list[CompiledPattern]] = {}
        self._no_word_patterns: list[CompiledPattern] = []  # Patterns starting with input (operators)

    def register(self, block_def: BlockDef) -> None:
        """Register a block definition."""
        compiled = compile_pattern(block_def)
        self._patterns.append(compiled)
        if compiled.first_word:
            self._by_first_word.setdefault(compiled.first_word, []).append(
                compiled
            )
        else:
            self._no_word_patterns.append(compiled)

    def register_all(self, block_defs: list[BlockDef]) -> None:
        """Register multiple block definitions."""
        for bd in block_defs:
            self.register(bd)

    def match_line(
        self,
        tokens: list[Token],
        start: int,
        end: int,
        context: str = "statement",
    ) -> Optional[tuple[BlockDef, dict[str, Any], int]]:
        """Try to match tokens[start:end] against registered patterns.

        Args:
            tokens: Full token list.
            start: Start index (inclusive).
            end: End index (exclusive) — typically the NEWLINE/EOF position.
            context: One of "hat", "statement", "reporter", "boolean".

        Returns:
            (block_def, captures, consumed_pos) or None.
            captures maps input/field names to their raw token ranges or values.
        """
        line_tokens = tokens[start:end]
        if not line_tokens:
            return None

        # Determine candidates based on first token
        candidates: list[CompiledPattern] = []

        first = line_tokens[0]
        if first.type == TokenType.WORD:
            word = first.value.lower()
            candidates = self._by_first_word.get(word, [])
        elif first.type in (TokenType.LPAREN, TokenType.LANGLE, TokenType.LBRACKET):
            candidates = self._no_word_patterns

        # Also try no-word patterns if word didn't match
        if not candidates and first.type == TokenType.WORD:
            candidates = self._no_word_patterns

        # Try each candidate
        for cp in candidates:
            if not self._shape_matches_context(cp.block_def.shape, context):
                continue
            result = self._try_match(cp, line_tokens)
            if result is not None:
                captures, consumed = result
                return (cp.block_def, captures, start + consumed)

        # If primary candidates failed, try all patterns as fallback
        for cp in self._patterns:
            if cp in candidates:
                continue
            if not self._shape_matches_context(cp.block_def.shape, context):
                continue
            result = self._try_match(cp, line_tokens)
            if result is not None:
                captures, consumed = result
                return (cp.block_def, captures, start + consumed)

        return None

    def _shape_matches_context(self, shape: BlockShape, context: str) -> bool:
        """Check if a block shape is valid for the given parse context."""
        if context == "hat":
            return shape == BlockShape.HAT
        elif context == "statement":
            return shape in (
                BlockShape.STACK,
                BlockShape.C_BLOCK,
                BlockShape.CAP,
            )
        elif context == "reporter":
            return shape in (BlockShape.REPORTER, BlockShape.BOOLEAN)
        elif context == "boolean":
            return shape == BlockShape.BOOLEAN
        return True  # "any" context

    def _try_match(
        self, cp: CompiledPattern, line_tokens: list[Token]
    ) -> Optional[tuple[dict[str, Any], int]]:
        """Try to match a compiled pattern against line tokens.

        Returns (captures_dict, tokens_consumed) or None.
        """
        captures: dict[str, Any] = {}
        tp = 0  # token position

        for elem in cp.elements:
            if tp >= len(line_tokens):
                return None  # Ran out of tokens

            tok = line_tokens[tp]

            if elem.kind == PatternElementKind.LITERAL:
                # Literal "<" matches LANGLE token, ">" matches RANGLE token
                if elem.value == "<":
                    if tok.type != TokenType.LANGLE:
                        return None
                elif elem.value == ">":
                    if tok.type != TokenType.RANGLE:
                        return None
                elif tok.type != TokenType.WORD or tok.value.lower() != elem.value:
                    return None
                tp += 1

            elif elem.kind == PatternElementKind.PAREN_INPUT:
                if tok.type != TokenType.LPAREN:
                    return None
                # Collect everything until matching RPAREN
                tp += 1
                inner_start = tp
                depth = 1
                while tp < len(line_tokens) and depth > 0:
                    if line_tokens[tp].type == TokenType.LPAREN:
                        depth += 1
                    elif line_tokens[tp].type == TokenType.RPAREN:
                        depth -= 1
                    if depth > 0:
                        tp += 1
                if depth != 0:
                    return None
                # line_tokens[inner_start:tp] is the content
                captures[elem.value] = line_tokens[inner_start:tp]
                tp += 1  # skip RPAREN

            elif elem.kind == PatternElementKind.BRACKET_FIELD:
                if tok.type != TokenType.LBRACKET:
                    return None
                tp += 1
                if tp >= len(line_tokens) or line_tokens[tp].type != TokenType.STRING:
                    return None
                field_value = line_tokens[tp].value
                tp += 1
                # Expect DROPDOWN_V
                if tp < len(line_tokens) and line_tokens[tp].type == TokenType.DROPDOWN_V:
                    tp += 1
                # Expect RBRACKET
                if tp >= len(line_tokens) or line_tokens[tp].type != TokenType.RBRACKET:
                    return None
                tp += 1
                captures[elem.value] = field_value

            elif elem.kind == PatternElementKind.BRACKET_INPUT:
                if tok.type == TokenType.LBRACKET:
                    tp += 1
                    if tp >= len(line_tokens) or line_tokens[tp].type != TokenType.STRING:
                        return None
                    str_value = line_tokens[tp].value
                    tp += 1
                    if tp >= len(line_tokens) or line_tokens[tp].type != TokenType.RBRACKET:
                        return None
                    tp += 1
                    captures[elem.value] = str_value
                elif tok.type == TokenType.LPAREN:
                    # Allow (value) in place of [value] — reporter/variable in string slot
                    tp += 1
                    inner_start = tp
                    depth = 1
                    while tp < len(line_tokens) and depth > 0:
                        if line_tokens[tp].type == TokenType.LPAREN:
                            depth += 1
                        elif line_tokens[tp].type == TokenType.RPAREN:
                            depth -= 1
                        if depth > 0:
                            tp += 1
                    if depth != 0:
                        return None
                    captures[elem.value] = line_tokens[inner_start:tp]
                    tp += 1  # skip RPAREN
                else:
                    return None

            elif elem.kind == PatternElementKind.ANGLE_INPUT:
                if tok.type != TokenType.LANGLE:
                    return None
                tp += 1
                inner_start = tp
                # Find the matching RANGLE.  Because `>` can appear
                # as a comparison operator *inside* the boolean slot,
                # simple depth counting fails.  Instead, collect all
                # RANGLE positions and try from the last one backwards
                # until the remaining pattern elements can be satisfied.
                rangle_positions: list[int] = []
                depth = 1
                scan = tp
                while scan < len(line_tokens):
                    if line_tokens[scan].type == TokenType.LANGLE:
                        depth += 1
                    elif line_tokens[scan].type == TokenType.RANGLE:
                        depth -= 1
                        if depth == 0:
                            rangle_positions.append(scan)
                            depth = 1  # keep scanning for later RANGLEs
                    scan += 1
                if not rangle_positions:
                    return None
                # Try from the last RANGLE backwards
                matched = False
                for rangle_pos in reversed(rangle_positions):
                    captures[elem.value] = line_tokens[inner_start:rangle_pos]
                    tp = rangle_pos + 1  # skip RANGLE
                    # Quick check: do remaining pattern elements plausibly fit?
                    remaining_literals = sum(
                        1 for e in cp.elements[cp.elements.index(elem) + 1:]
                        if e.kind == PatternElementKind.LITERAL
                    )
                    remaining_tokens = len(line_tokens) - tp
                    if remaining_tokens >= remaining_literals:
                        matched = True
                        break
                if not matched:
                    return None

        # Check that we consumed all tokens (no leftover)
        if tp != len(line_tokens):
            return None

        return captures, tp
