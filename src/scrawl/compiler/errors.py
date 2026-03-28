"""Error classes for the ScratchText compiler."""

from __future__ import annotations

from typing import Optional

from scrawl.errors import ScrawlError


class CompileError(ScrawlError):
    """Base compile error."""

    def __init__(
        self,
        message: str,
        line: Optional[int] = None,
        col: Optional[int] = None,
    ):
        self.line = line
        self.col = col
        loc = f" at line {line}" if line else ""
        super().__init__(f"Compile error{loc}: {message}")


class LexerError(CompileError):
    """Tokenization error (unmatched bracket, invalid character, etc.)."""

    pass


class ParseError(CompileError):
    """Parser error (unexpected token, unrecognized block, etc.)."""

    pass


class UnknownBlockError(ParseError):
    """No registry match for a block line."""

    pass


class UnclosedBlockError(ParseError):
    """Missing 'end' for a C-block."""

    pass


class CodeGenError(CompileError):
    """Error during code generation (unresolvable reference, etc.)."""

    pass
