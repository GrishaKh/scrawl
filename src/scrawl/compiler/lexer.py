"""Lexer for the ScratchText language.

Tokenizes source text line by line into a flat stream of tokens.
No block/opcode recognition happens here — that's the parser's job.
"""

from __future__ import annotations

import re
from typing import Optional

from scrawl.compiler.errors import LexerError
from scrawl.compiler.tokens import Token, TokenType

# Regex for detecting numbers (including negatives and decimals)
_NUMBER_RE = re.compile(r"^-?(?:\d+\.?\d*|\.\d+)$")

# Regex for hex color codes
_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")

# Characters that are word-breakers (delimiters)
_DELIMITERS = set("()[]<>")


class Lexer:
    """Tokenize ScratchText source into a list of tokens."""

    def __init__(self, source: str):
        self.source = source
        self.tokens: list[Token] = []
        self.line = 0
        self.col = 0

    def tokenize(self) -> list[Token]:
        """Tokenize the full source and return the token list."""
        self.tokens = []
        lines = self.source.split("\n")

        for line_num, raw_line in enumerate(lines, start=1):
            self.line = line_num
            stripped = raw_line.strip()

            # Skip blank lines and comments
            if not stripped or stripped.startswith("//") or stripped.startswith("#"):
                # Blank lines emit NEWLINE to help parser detect script boundaries
                if not stripped:
                    self.tokens.append(
                        Token(TokenType.NEWLINE, None, line_num, 0)
                    )
                continue

            self._tokenize_line(stripped, line_num)
            self.tokens.append(Token(TokenType.NEWLINE, None, line_num, 0))

        self.tokens.append(Token(TokenType.EOF, None, self.line + 1, 0))
        return self.tokens

    def _tokenize_line(self, text: str, line_num: int) -> None:
        """Tokenize a single stripped line."""
        i = 0
        while i < len(text):
            ch = text[i]

            # Skip whitespace
            if ch == " " or ch == "\t":
                i += 1
                continue

            # Parenthesized value: (...)
            if ch == "(":
                i = self._read_paren(text, i, line_num)
                continue

            # Bracketed value: [...]
            if ch == "[":
                i = self._read_bracket(text, i, line_num)
                continue

            # Angle bracket (boolean reporter)
            if ch == "<":
                self.tokens.append(
                    Token(TokenType.LANGLE, None, line_num, i + 1)
                )
                i += 1
                continue

            if ch == ">":
                self.tokens.append(
                    Token(TokenType.RANGLE, None, line_num, i + 1)
                )
                i += 1
                continue

            # Word token
            i = self._read_word(text, i, line_num)

    def _read_paren(self, text: str, start: int, line_num: int) -> int:
        """Read a parenthesized value: (content).

        Emits LPAREN, content token(s), RPAREN.
        Content can be a NUMBER, STRING, COLOR, or recursively tokenized
        if it contains nested delimiters.
        """
        col = start + 1
        self.tokens.append(Token(TokenType.LPAREN, None, line_num, col))

        # Find matching closing paren
        depth = 1
        i = start + 1
        while i < len(text) and depth > 0:
            if text[i] == "(":
                depth += 1
            elif text[i] == ")":
                depth -= 1
            i += 1

        if depth != 0:
            raise LexerError("Unmatched '('", line=line_num, col=col)

        # Content is text[start+1 : i-1]
        content = text[start + 1 : i - 1].strip()
        inner_col = start + 2

        if not content:
            # Empty parens — emit empty string
            self.tokens.append(
                Token(TokenType.STRING, "", line_num, inner_col)
            )
        elif self._has_nested_delimiters(content):
            # Content has nested <, (, [ — tokenize recursively
            self._tokenize_line(content, line_num)
        elif _COLOR_RE.match(content):
            self.tokens.append(
                Token(TokenType.COLOR, content, line_num, inner_col)
            )
        elif _NUMBER_RE.match(content):
            self.tokens.append(
                Token(TokenType.NUMBER, content, line_num, inner_col)
            )
        else:
            # Treat as string (could be variable name or literal)
            self.tokens.append(
                Token(TokenType.STRING, content, line_num, inner_col)
            )

        self.tokens.append(Token(TokenType.RPAREN, None, line_num, i))
        return i

    def _read_bracket(self, text: str, start: int, line_num: int) -> int:
        """Read a bracketed value: [content] or [content v].

        Emits LBRACKET, STRING, optional DROPDOWN_V, RBRACKET.
        """
        col = start + 1
        self.tokens.append(Token(TokenType.LBRACKET, None, line_num, col))

        # Find matching closing bracket
        i = start + 1
        while i < len(text) and text[i] != "]":
            i += 1

        if i >= len(text):
            raise LexerError("Unmatched '['", line=line_num, col=col)

        content = text[start + 1 : i]
        inner_col = start + 2

        # Check for dropdown indicator: trailing " v"
        if content.endswith(" v") and len(content) > 2:
            actual_value = content[:-2]
            self.tokens.append(
                Token(TokenType.STRING, actual_value, line_num, inner_col)
            )
            self.tokens.append(
                Token(TokenType.DROPDOWN_V, "v", line_num, i - 1)
            )
        else:
            self.tokens.append(
                Token(TokenType.STRING, content, line_num, inner_col)
            )

        self.tokens.append(Token(TokenType.RBRACKET, None, line_num, i + 1))
        return i + 1

    def _read_word(self, text: str, start: int, line_num: int) -> int:
        """Read a word token (contiguous non-whitespace, non-delimiter chars)."""
        i = start
        while i < len(text) and text[i] not in " \t" and text[i] not in _DELIMITERS:
            i += 1

        word = text[start:i]
        col = start + 1

        # Check for special keywords
        lower = word.lower()
        if lower == "end":
            self.tokens.append(Token(TokenType.END, "end", line_num, col))
        elif lower == "else":
            self.tokens.append(Token(TokenType.ELSE, "else", line_num, col))
        elif lower == "define":
            self.tokens.append(
                Token(TokenType.DEFINE, "define", line_num, col)
            )
        else:
            self.tokens.append(Token(TokenType.WORD, word, line_num, col))

        return i

    def _has_nested_delimiters(self, content: str) -> bool:
        """Check if content contains nested delimiters that need recursive tokenization."""
        for ch in content:
            if ch in _DELIMITERS:
                return True
        return False
