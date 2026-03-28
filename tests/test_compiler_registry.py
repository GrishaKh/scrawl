"""Tests for the opcode registry and pattern matching."""

from __future__ import annotations

import pytest

from scrawl.compiler.registry import (
    BlockDef,
    BlockRegistry,
    BlockShape,
    CompiledPattern,
    InputSpec,
    FieldSpec,
    MenuSpec,
    PatternElement,
    PatternElementKind,
    compile_pattern,
)
from scrawl.compiler.registry_data import ALL_BLOCKS
from scrawl.compiler.tokens import Token, TokenType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_token(ttype: TokenType, value=None, line=1, col=0):
    return Token(ttype, value, line, col)


def make_word(value: str, line=1, col=0):
    return Token(TokenType.WORD, value, line, col)


# ---------------------------------------------------------------------------
# Pattern compilation
# ---------------------------------------------------------------------------


class TestPatternCompilation:
    def test_simple_literal(self):
        bd = BlockDef(pattern="show", opcode="looks_show", shape=BlockShape.STACK)
        cp = compile_pattern(bd)
        assert len(cp.elements) == 1
        assert cp.elements[0].kind == PatternElementKind.LITERAL
        assert cp.elements[0].value == "show"
        assert cp.first_word == "show"

    def test_paren_input(self):
        bd = BlockDef(
            pattern="move (STEPS) steps",
            opcode="motion_movesteps",
            shape=BlockShape.STACK,
            inputs=[InputSpec("STEPS", "number", "10", 4)],
        )
        cp = compile_pattern(bd)
        assert len(cp.elements) == 3
        assert cp.elements[0].kind == PatternElementKind.LITERAL
        assert cp.elements[0].value == "move"
        assert cp.elements[1].kind == PatternElementKind.PAREN_INPUT
        assert cp.elements[1].value == "STEPS"
        assert cp.elements[2].kind == PatternElementKind.LITERAL
        assert cp.elements[2].value == "steps"

    def test_bracket_field(self):
        bd = BlockDef(
            pattern="set [VARIABLE v] to (VALUE)",
            opcode="data_setvariableto",
            shape=BlockShape.STACK,
            inputs=[InputSpec("VALUE", "string", "0", 10)],
            fields=[FieldSpec("VARIABLE", "variable")],
        )
        cp = compile_pattern(bd)
        bracket_elem = [e for e in cp.elements if e.kind == PatternElementKind.BRACKET_FIELD]
        assert len(bracket_elem) == 1
        assert bracket_elem[0].value == "VARIABLE"

    def test_bracket_input(self):
        bd = BlockDef(
            pattern="say [MESSAGE]",
            opcode="looks_say",
            shape=BlockShape.STACK,
            inputs=[InputSpec("MESSAGE", "string", "Hello!", 10)],
        )
        cp = compile_pattern(bd)
        bracket_elem = [e for e in cp.elements if e.kind == PatternElementKind.BRACKET_INPUT]
        assert len(bracket_elem) == 1
        assert bracket_elem[0].value == "MESSAGE"

    def test_angle_input(self):
        bd = BlockDef(
            pattern="if <CONDITION> then",
            opcode="control_if",
            shape=BlockShape.C_BLOCK,
            inputs=[InputSpec("CONDITION", "boolean")],
            substacks=1,
        )
        cp = compile_pattern(bd)
        angle_elem = [e for e in cp.elements if e.kind == PatternElementKind.ANGLE_INPUT]
        assert len(angle_elem) == 1
        assert angle_elem[0].value == "CONDITION"

    def test_operator_lt_pattern(self):
        """The < in '(A) < (B)' should be a LITERAL, not an angle bracket."""
        bd = BlockDef(
            pattern="(OPERAND1) < (OPERAND2)",
            opcode="operator_lt",
            shape=BlockShape.BOOLEAN,
            inputs=[
                InputSpec("OPERAND1", "string", "", 10),
                InputSpec("OPERAND2", "string", "", 10),
            ],
            has_next=False,
        )
        cp = compile_pattern(bd)
        literals = [e for e in cp.elements if e.kind == PatternElementKind.LITERAL]
        assert len(literals) == 1
        assert literals[0].value == "<"

    def test_operator_gt_pattern(self):
        """The > in '(A) > (B)' should be a LITERAL."""
        bd = BlockDef(
            pattern="(OPERAND1) > (OPERAND2)",
            opcode="operator_gt",
            shape=BlockShape.BOOLEAN,
        )
        cp = compile_pattern(bd)
        literals = [e for e in cp.elements if e.kind == PatternElementKind.LITERAL]
        assert len(literals) == 1
        assert literals[0].value == ">"

    def test_all_blocks_compile(self):
        """All block definitions in registry_data should compile without error."""
        for bd in ALL_BLOCKS:
            cp = compile_pattern(bd)
            assert isinstance(cp, CompiledPattern)
        assert len(ALL_BLOCKS) >= 130  # We have 132 blocks after Phase 2

    def test_no_duplicate_opcodes_in_same_shape(self):
        """No two patterns with the same opcode AND shape should exist
        unless they're intentional variants (e.g., costume number vs name)."""
        seen: dict[tuple[str, str], str] = {}
        for bd in ALL_BLOCKS:
            key = (bd.opcode, bd.shape.name)
            # Allow known variants
            if bd.opcode in ("looks_costumenumbername", "looks_backdropnumbername"):
                continue
            if key in seen:
                assert False, f"Duplicate opcode+shape: {bd.opcode} ({bd.shape.name}) — patterns: '{seen[key]}' and '{bd.pattern}'"
            seen[key] = bd.pattern


# ---------------------------------------------------------------------------
# Registry matching
# ---------------------------------------------------------------------------


class TestRegistryMatching:
    @pytest.fixture()
    def registry(self):
        reg = BlockRegistry()
        reg.register_all(ALL_BLOCKS)
        return reg

    def test_match_simple_command(self, registry):
        """Match 'show' as looks_show."""
        tokens = [make_word("show")]
        result = registry.match_line(tokens, 0, 1, context="statement")
        assert result is not None
        block_def, captures, consumed = result
        assert block_def.opcode == "looks_show"

    def test_match_move_steps(self, registry):
        """Match 'move (10) steps'."""
        tokens = [
            make_word("move"),
            make_token(TokenType.LPAREN),
            make_token(TokenType.NUMBER, "10"),
            make_token(TokenType.RPAREN),
            make_word("steps"),
        ]
        result = registry.match_line(tokens, 0, 5, context="statement")
        assert result is not None
        block_def, captures, consumed = result
        assert block_def.opcode == "motion_movesteps"
        assert "STEPS" in captures

    def test_match_set_variable(self, registry):
        """Match 'set [score v] to (0)'."""
        tokens = [
            make_word("set"),
            make_token(TokenType.LBRACKET),
            make_token(TokenType.STRING, "score"),
            make_token(TokenType.DROPDOWN_V, "v"),
            make_token(TokenType.RBRACKET),
            make_word("to"),
            make_token(TokenType.LPAREN),
            make_token(TokenType.NUMBER, "0"),
            make_token(TokenType.RPAREN),
        ]
        result = registry.match_line(tokens, 0, 9, context="statement")
        assert result is not None
        block_def, captures, consumed = result
        assert block_def.opcode == "data_setvariableto"
        assert captures["VARIABLE"] == "score"

    def test_match_hat_context(self, registry):
        """Hat blocks should only match in hat context."""
        tokens = [make_word("when"), make_word("flag"), make_word("clicked")]
        result_hat = registry.match_line(tokens, 0, 3, context="hat")
        result_stmt = registry.match_line(tokens, 0, 3, context="statement")
        assert result_hat is not None
        assert result_hat[0].opcode == "event_whenflagclicked"
        assert result_stmt is None  # Should NOT match as a statement

    def test_match_boolean_context(self, registry):
        """Boolean blocks should match in boolean context."""
        tokens = [
            make_word("mouse"),
            make_word("down?"),
        ]
        result = registry.match_line(tokens, 0, 2, context="boolean")
        assert result is not None
        assert result[0].opcode == "sensing_mousedown"

    def test_match_operator_gt(self, registry):
        """Match '(x) > (5)' with > as RANGLE token."""
        tokens = [
            make_token(TokenType.LPAREN),
            make_token(TokenType.STRING, "x"),
            make_token(TokenType.RPAREN),
            make_token(TokenType.RANGLE),  # > as token
            make_token(TokenType.LPAREN),
            make_token(TokenType.NUMBER, "5"),
            make_token(TokenType.RPAREN),
        ]
        result = registry.match_line(tokens, 0, 7, context="boolean")
        assert result is not None
        assert result[0].opcode == "operator_gt"

    def test_match_operator_lt(self, registry):
        """Match '(x) < (5)' with < as LANGLE token."""
        tokens = [
            make_token(TokenType.LPAREN),
            make_token(TokenType.STRING, "x"),
            make_token(TokenType.RPAREN),
            make_token(TokenType.LANGLE),  # < as token
            make_token(TokenType.LPAREN),
            make_token(TokenType.NUMBER, "5"),
            make_token(TokenType.RPAREN),
        ]
        result = registry.match_line(tokens, 0, 7, context="boolean")
        assert result is not None
        assert result[0].opcode == "operator_lt"

    def test_no_match_returns_none(self, registry):
        """Gibberish tokens should not match."""
        tokens = [make_word("xyzzy"), make_word("plugh")]
        result = registry.match_line(tokens, 0, 2, context="statement")
        assert result is None

    def test_bracket_input_accepts_paren(self, registry):
        """[MESSAGE] slots should also accept (value) tokens."""
        # say (variable) for (2) seconds
        tokens = [
            make_word("say"),
            make_token(TokenType.LPAREN),
            make_token(TokenType.STRING, "greeting"),
            make_token(TokenType.RPAREN),
            make_word("for"),
            make_token(TokenType.LPAREN),
            make_token(TokenType.NUMBER, "2"),
            make_token(TokenType.RPAREN),
            make_word("seconds"),
        ]
        result = registry.match_line(tokens, 0, 9, context="statement")
        assert result is not None
        assert result[0].opcode == "looks_sayforsecs"

    def test_angle_input_with_gt_operator(self, registry):
        """<(score) > (10)> should match with > inside angle brackets."""
        tokens = [
            make_word("if"),
            make_token(TokenType.LANGLE),
            make_token(TokenType.LPAREN),
            make_token(TokenType.STRING, "score"),
            make_token(TokenType.RPAREN),
            make_token(TokenType.RANGLE),  # > operator (could be close)
            make_token(TokenType.LPAREN),
            make_token(TokenType.NUMBER, "10"),
            make_token(TokenType.RPAREN),
            make_token(TokenType.RANGLE),  # actual close
            make_word("then"),
        ]
        result = registry.match_line(tokens, 0, 11, context="statement")
        assert result is not None
        assert result[0].opcode == "control_if"
        assert "CONDITION" in result[1]

    # -- Phase 2 matching tests --

    def test_match_wait_until(self, registry):
        """Match 'wait until <CONDITION>'."""
        tokens = [
            make_word("wait"),
            make_word("until"),
            make_token(TokenType.LANGLE),
            make_word("mouse"),
            make_word("down?"),
            make_token(TokenType.RANGLE),
        ]
        result = registry.match_line(tokens, 0, 6, context="statement")
        assert result is not None
        assert result[0].opcode == "control_wait_until"

    def test_match_if_on_edge_bounce(self, registry):
        """Match 'if on edge, bounce'."""
        tokens = [
            make_word("if"),
            make_word("on"),
            make_word("edge,"),
            make_word("bounce"),
        ]
        result = registry.match_line(tokens, 0, 4, context="statement")
        assert result is not None
        assert result[0].opcode == "motion_ifonedgebounce"

    def test_match_round_reporter(self, registry):
        """Match 'round (NUM)' as reporter."""
        tokens = [
            make_word("round"),
            make_token(TokenType.LPAREN),
            make_token(TokenType.NUMBER, "3.7"),
            make_token(TokenType.RPAREN),
        ]
        result = registry.match_line(tokens, 0, 4, context="reporter")
        assert result is not None
        assert result[0].opcode == "operator_round"

    def test_match_operator_mod(self, registry):
        """Match '(A) mod (B)' as reporter."""
        tokens = [
            make_token(TokenType.LPAREN),
            make_token(TokenType.NUMBER, "10"),
            make_token(TokenType.RPAREN),
            make_word("mod"),
            make_token(TokenType.LPAREN),
            make_token(TokenType.NUMBER, "3"),
            make_token(TokenType.RPAREN),
        ]
        result = registry.match_line(tokens, 0, 7, context="reporter")
        assert result is not None
        assert result[0].opcode == "operator_mod"

    def test_match_sound_play_until_done(self, registry):
        """Match 'play sound [pop v] until done'."""
        tokens = [
            make_word("play"),
            make_word("sound"),
            make_token(TokenType.LBRACKET),
            make_token(TokenType.STRING, "pop"),
            make_token(TokenType.DROPDOWN_V, "v"),
            make_token(TokenType.RBRACKET),
            make_word("until"),
            make_word("done"),
        ]
        result = registry.match_line(tokens, 0, 8, context="statement")
        assert result is not None
        assert result[0].opcode == "sound_playuntildone"

    def test_match_set_volume(self, registry):
        """Match 'set volume to (100) %'."""
        tokens = [
            make_word("set"),
            make_word("volume"),
            make_word("to"),
            make_token(TokenType.LPAREN),
            make_token(TokenType.NUMBER, "100"),
            make_token(TokenType.RPAREN),
            make_word("%"),
        ]
        result = registry.match_line(tokens, 0, 7, context="statement")
        assert result is not None
        assert result[0].opcode == "sound_setvolumeto"

    def test_match_clear_graphic_effects(self, registry):
        """Match 'clear graphic effects'."""
        tokens = [
            make_word("clear"),
            make_word("graphic"),
            make_word("effects"),
        ]
        result = registry.match_line(tokens, 0, 3, context="statement")
        assert result is not None
        assert result[0].opcode == "looks_cleargraphiceffects"

    def test_match_costume_number_reporter(self, registry):
        """Match 'costume number' as reporter."""
        tokens = [make_word("costume"), make_word("number")]
        result = registry.match_line(tokens, 0, 2, context="reporter")
        assert result is not None
        assert result[0].opcode == "looks_costumenumbername"

    def test_match_costume_name_reporter(self, registry):
        """Match 'costume name' as reporter."""
        tokens = [make_word("costume"), make_word("name")]
        result = registry.match_line(tokens, 0, 2, context="reporter")
        assert result is not None
        assert result[0].opcode == "looks_costumenumbername"

    def test_match_volume_reporter(self, registry):
        """Match 'volume' as reporter."""
        tokens = [make_word("volume")]
        result = registry.match_line(tokens, 0, 1, context="reporter")
        assert result is not None
        assert result[0].opcode == "sound_volume"

    def test_match_days_since_2000(self, registry):
        """Match 'days since 2000' as reporter."""
        tokens = [
            make_word("days"),
            make_word("since"),
            make_word("2000"),
        ]
        result = registry.match_line(tokens, 0, 3, context="reporter")
        assert result is not None
        assert result[0].opcode == "sensing_dayssince2000"

    def test_match_touching_color(self, registry):
        """Match 'touching color (#ff0000)?' as boolean."""
        tokens = [
            make_word("touching"),
            make_word("color"),
            make_token(TokenType.LPAREN),
            make_token(TokenType.COLOR, "#ff0000"),
            make_token(TokenType.RPAREN),
            make_word("?"),
        ]
        result = registry.match_line(tokens, 0, 6, context="boolean")
        assert result is not None
        assert result[0].opcode == "sensing_touchingcolor"

    def test_sound_effect_no_collision(self, registry):
        """'change [pitch v] sound effect by (10)' should NOT match looks_changeeffectby."""
        tokens = [
            make_word("change"),
            make_token(TokenType.LBRACKET),
            make_token(TokenType.STRING, "pitch"),
            make_token(TokenType.DROPDOWN_V, "v"),
            make_token(TokenType.RBRACKET),
            make_word("sound"),
            make_word("effect"),
            make_word("by"),
            make_token(TokenType.LPAREN),
            make_token(TokenType.NUMBER, "10"),
            make_token(TokenType.RPAREN),
        ]
        result = registry.match_line(tokens, 0, 11, context="statement")
        assert result is not None
        assert result[0].opcode == "sound_changeeffectby"

    def test_looks_effect_no_collision(self, registry):
        """'change [color v] effect by (25)' should match looks_changeeffectby."""
        tokens = [
            make_word("change"),
            make_token(TokenType.LBRACKET),
            make_token(TokenType.STRING, "color"),
            make_token(TokenType.DROPDOWN_V, "v"),
            make_token(TokenType.RBRACKET),
            make_word("effect"),
            make_word("by"),
            make_token(TokenType.LPAREN),
            make_token(TokenType.NUMBER, "25"),
            make_token(TokenType.RPAREN),
        ]
        result = registry.match_line(tokens, 0, 10, context="statement")
        assert result is not None
        assert result[0].opcode == "looks_changeeffectby"
