"""Tests for the ScratchText lexer."""

from __future__ import annotations

import pytest

from scrawl.compiler.lexer import Lexer
from scrawl.compiler.tokens import Token, TokenType
from scrawl.compiler.errors import LexerError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def tokenize(text: str) -> list[Token]:
    """Tokenize text and return tokens (excluding EOF)."""
    return Lexer(text).tokenize()


def token_types(text: str) -> list[TokenType]:
    """Return just the token types for a given source line."""
    tokens = tokenize(text)
    return [t.type for t in tokens]


def token_values(text: str) -> list:
    """Return (type, value) tuples for inspection."""
    tokens = tokenize(text)
    return [(t.type, t.value) for t in tokens]


# ---------------------------------------------------------------------------
# Basic tokens
# ---------------------------------------------------------------------------


class TestBasicTokens:
    def test_empty_string(self):
        tokens = tokenize("")
        assert tokens[-1].type == TokenType.EOF
        # Empty string produces at least NEWLINE + EOF
        assert len(tokens) >= 1

    def test_blank_line(self):
        tokens = tokenize("\n")
        types = [t.type for t in tokens]
        assert TokenType.NEWLINE in types

    def test_single_word(self):
        tokens = tokenize("move")
        types = [t.type for t in tokens]
        assert types == [TokenType.WORD, TokenType.NEWLINE, TokenType.EOF]
        assert tokens[0].value == "move"

    def test_multiple_words(self):
        tokens = tokenize("turn right")
        word_tokens = [t for t in tokens if t.type == TokenType.WORD]
        assert len(word_tokens) == 2
        assert word_tokens[0].value == "turn"
        assert word_tokens[1].value == "right"

    def test_comment_line_skipped(self):
        tokens = tokenize("// this is a comment")
        types = [t.type for t in tokens]
        assert TokenType.WORD not in types

    def test_hash_comment_skipped(self):
        tokens = tokenize("# this is a comment")
        types = [t.type for t in tokens]
        assert TokenType.WORD not in types


# ---------------------------------------------------------------------------
# Parenthesized values
# ---------------------------------------------------------------------------


class TestParentheses:
    def test_number(self):
        tokens = tokenize("(10)")
        vals = [(t.type, t.value) for t in tokens if t.type not in (TokenType.NEWLINE, TokenType.EOF)]
        assert vals == [
            (TokenType.LPAREN, None),
            (TokenType.NUMBER, "10"),
            (TokenType.RPAREN, None),
        ]

    def test_negative_number(self):
        tokens = tokenize("(-5)")
        nums = [t for t in tokens if t.type == TokenType.NUMBER]
        assert len(nums) == 1
        assert nums[0].value == "-5"

    def test_decimal_number(self):
        tokens = tokenize("(3.14)")
        nums = [t for t in tokens if t.type == TokenType.NUMBER]
        assert nums[0].value == "3.14"

    def test_string_value(self):
        tokens = tokenize("(hello)")
        strs = [t for t in tokens if t.type == TokenType.STRING]
        assert len(strs) == 1
        assert strs[0].value == "hello"

    def test_empty_parens(self):
        tokens = tokenize("()")
        strs = [t for t in tokens if t.type == TokenType.STRING]
        assert len(strs) == 1
        assert strs[0].value == ""

    def test_color_code(self):
        tokens = tokenize("(#ff0000)")
        colors = [t for t in tokens if t.type == TokenType.COLOR]
        assert len(colors) == 1
        assert colors[0].value == "#ff0000"

    def test_nested_parens(self):
        """Nested parens should be tokenized recursively."""
        tokens = tokenize("((10) + (20))")
        types = [t.type for t in tokens if t.type not in (TokenType.NEWLINE, TokenType.EOF)]
        assert TokenType.LPAREN in types
        assert TokenType.RPAREN in types
        # Should have inner LPAREN/RPAREN pairs too
        lparen_count = sum(1 for t in types if t == TokenType.LPAREN)
        rparen_count = sum(1 for t in types if t == TokenType.RPAREN)
        assert lparen_count == 3  # outer + 2 inner
        assert rparen_count == 3

    def test_unmatched_paren_raises(self):
        with pytest.raises(LexerError):
            tokenize("(unclosed")


# ---------------------------------------------------------------------------
# Bracketed values
# ---------------------------------------------------------------------------


class TestBrackets:
    def test_simple_bracket(self):
        tokens = tokenize("[hello]")
        vals = [(t.type, t.value) for t in tokens if t.type not in (TokenType.NEWLINE, TokenType.EOF)]
        assert vals == [
            (TokenType.LBRACKET, None),
            (TokenType.STRING, "hello"),
            (TokenType.RBRACKET, None),
        ]

    def test_dropdown_bracket(self):
        tokens = tokenize("[mouse-pointer v]")
        vals = [(t.type, t.value) for t in tokens if t.type not in (TokenType.NEWLINE, TokenType.EOF)]
        assert vals == [
            (TokenType.LBRACKET, None),
            (TokenType.STRING, "mouse-pointer"),
            (TokenType.DROPDOWN_V, "v"),
            (TokenType.RBRACKET, None),
        ]

    def test_unmatched_bracket_raises(self):
        with pytest.raises(LexerError):
            tokenize("[unclosed")


# ---------------------------------------------------------------------------
# Angle brackets
# ---------------------------------------------------------------------------


class TestAngleBrackets:
    def test_angle_brackets(self):
        tokens = tokenize("<test>")
        types = [t.type for t in tokens if t.type not in (TokenType.NEWLINE, TokenType.EOF)]
        assert types == [TokenType.LANGLE, TokenType.WORD, TokenType.RANGLE]

    def test_angle_with_content(self):
        tokens = tokenize("<touching [mouse-pointer v]?>")
        types = [t.type for t in tokens if t.type not in (TokenType.NEWLINE, TokenType.EOF)]
        assert TokenType.LANGLE in types
        assert TokenType.RANGLE in types


# ---------------------------------------------------------------------------
# Keywords
# ---------------------------------------------------------------------------


class TestKeywords:
    def test_end_keyword(self):
        tokens = tokenize("end")
        assert tokens[0].type == TokenType.END
        assert tokens[0].value == "end"

    def test_else_keyword(self):
        tokens = tokenize("else")
        assert tokens[0].type == TokenType.ELSE
        assert tokens[0].value == "else"

    def test_define_keyword(self):
        tokens = tokenize("define")
        assert tokens[0].type == TokenType.DEFINE
        assert tokens[0].value == "define"

    def test_keywords_case_insensitive(self):
        tokens = tokenize("END")
        assert tokens[0].type == TokenType.END

        tokens = tokenize("Else")
        assert tokens[0].type == TokenType.ELSE


# ---------------------------------------------------------------------------
# Full line tokenization
# ---------------------------------------------------------------------------


class TestFullLines:
    def test_move_steps(self):
        tokens = tokenize("move (10) steps")
        types = [t.type for t in tokens if t.type not in (TokenType.NEWLINE, TokenType.EOF)]
        assert types == [
            TokenType.WORD,     # move
            TokenType.LPAREN,   # (
            TokenType.NUMBER,   # 10
            TokenType.RPAREN,   # )
            TokenType.WORD,     # steps
        ]

    def test_set_variable(self):
        tokens = tokenize("set [score v] to (0)")
        types = [t.type for t in tokens if t.type not in (TokenType.NEWLINE, TokenType.EOF)]
        expected = [
            TokenType.WORD,       # set
            TokenType.LBRACKET,   # [
            TokenType.STRING,     # score
            TokenType.DROPDOWN_V, # v
            TokenType.RBRACKET,   # ]
            TokenType.WORD,       # to
            TokenType.LPAREN,     # (
            TokenType.NUMBER,     # 0
            TokenType.RPAREN,     # )
        ]
        assert types == expected

    def test_if_then_with_boolean(self):
        tokens = tokenize("if <touching [mouse-pointer v]?> then")
        types = [t.type for t in tokens if t.type not in (TokenType.NEWLINE, TokenType.EOF)]
        assert types[0] == TokenType.WORD  # if
        assert types[1] == TokenType.LANGLE  # <
        assert types[-1] == TokenType.WORD  # then

    def test_multiline_script(self):
        source = "when flag clicked\nmove (10) steps\nend"
        tokens = tokenize(source)
        newlines = [t for t in tokens if t.type == TokenType.NEWLINE]
        assert len(newlines) == 3  # after each line

    def test_line_numbers(self):
        source = "move (10) steps\nturn right (15) degrees"
        tokens = tokenize(source)
        line1_tokens = [t for t in tokens if t.line == 1 and t.type == TokenType.WORD]
        line2_tokens = [t for t in tokens if t.line == 2 and t.type == TokenType.WORD]
        assert len(line1_tokens) == 2  # move, steps
        assert len(line2_tokens) == 3  # turn, right, degrees

    def test_blank_line_between_scripts(self):
        source = "when flag clicked\n\nwhen this sprite clicked"
        tokens = tokenize(source)
        newlines = [t for t in tokens if t.type == TokenType.NEWLINE]
        assert len(newlines) >= 2  # At least the blank line newline
