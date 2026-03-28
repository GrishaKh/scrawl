"""Token types and Token dataclass for the ScratchText lexer."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Optional


class TokenType(Enum):
    """All token types produced by the lexer."""

    # Structural
    NEWLINE = auto()
    EOF = auto()

    # Delimiters
    LPAREN = auto()      # (
    RPAREN = auto()      # )
    LBRACKET = auto()    # [
    RBRACKET = auto()    # ]
    LANGLE = auto()      # <
    RANGLE = auto()      # >

    # Values
    NUMBER = auto()      # 10, 3.14, -5
    STRING = auto()      # text inside () or []
    COLOR = auto()       # #ff0000

    # Identifiers and keywords
    WORD = auto()        # Any word token (move, steps, forever, etc.)
    DROPDOWN_V = auto()  # The trailing "v" in [dropdown v]

    # Special keywords
    END = auto()         # "end" keyword (C-block closer)
    ELSE = auto()        # "else" keyword (if/else separator)
    DEFINE = auto()      # "define" keyword (custom block definer)


@dataclass(frozen=True)
class Token:
    """A single token from the lexer."""

    type: TokenType
    value: Any
    line: int
    col: int

    def __repr__(self) -> str:
        if self.value is not None:
            return f"Token({self.type.name}, {self.value!r}, L{self.line}:{self.col})"
        return f"Token({self.type.name}, L{self.line}:{self.col})"
