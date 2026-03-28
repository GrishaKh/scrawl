"""Tests for the ScratchText parser."""

from __future__ import annotations

import pytest

from scrawl.compiler.ast_nodes import (
    BlockNode,
    BroadcastInput,
    CustomBlockDef,
    FieldNode,
    LiteralInput,
    ReporterInput,
    ScriptNode,
    StatementNode,
    VariableInput,
)
from scrawl.compiler.errors import UnknownBlockError, UnclosedBlockError
from scrawl.compiler.lexer import Lexer
from scrawl.compiler.parser import Parser
from scrawl.compiler.registry import BlockRegistry
from scrawl.compiler.registry_data import ALL_BLOCKS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_registry() -> BlockRegistry:
    reg = BlockRegistry()
    reg.register_all(ALL_BLOCKS)
    return reg


def parse(source: str) -> list[ScriptNode | CustomBlockDef]:
    tokens = Lexer(source).tokenize()
    return Parser(tokens, make_registry()).parse()


# ---------------------------------------------------------------------------
# Basic script parsing
# ---------------------------------------------------------------------------


class TestBasicParsing:
    def test_single_hat(self):
        scripts = parse("when flag clicked")
        assert len(scripts) == 1
        assert isinstance(scripts[0], ScriptNode)
        assert scripts[0].hat.opcode == "event_whenflagclicked"
        assert scripts[0].body == []

    def test_hat_with_body(self):
        scripts = parse("when flag clicked\nmove (10) steps")
        assert len(scripts) == 1
        script = scripts[0]
        assert script.hat.opcode == "event_whenflagclicked"
        assert len(script.body) == 1
        assert script.body[0].block.opcode == "motion_movesteps"

    def test_hat_with_multiple_statements(self):
        source = """when flag clicked
move (10) steps
turn right (15) degrees
say [Hello!]"""
        scripts = parse(source)
        assert len(scripts) == 1
        assert len(scripts[0].body) == 3

    def test_multiple_scripts(self):
        source = """when flag clicked
move (10) steps

when this sprite clicked
say [Hi!]"""
        scripts = parse(source)
        assert len(scripts) == 2
        assert scripts[0].hat.opcode == "event_whenflagclicked"
        assert scripts[1].hat.opcode == "event_whenthisspriteclicked"

    def test_empty_source(self):
        scripts = parse("")
        assert scripts == []

    def test_comments_ignored(self):
        source = """// This is a comment
when flag clicked
# Another comment
move (10) steps"""
        scripts = parse(source)
        assert len(scripts) == 1
        assert len(scripts[0].body) == 1


# ---------------------------------------------------------------------------
# Input resolution
# ---------------------------------------------------------------------------


class TestInputResolution:
    def test_number_input(self):
        scripts = parse("when flag clicked\nmove (10) steps")
        stmt = scripts[0].body[0]
        steps_input = stmt.block.inputs.get("STEPS")
        assert isinstance(steps_input, LiteralInput)
        assert steps_input.value == "10"

    def test_variable_input(self):
        scripts = parse("when flag clicked\nmove (speed) steps")
        stmt = scripts[0].body[0]
        steps_input = stmt.block.inputs.get("STEPS")
        assert isinstance(steps_input, VariableInput)
        assert steps_input.name == "speed"

    def test_broadcast_input(self):
        scripts = parse("when flag clicked\nbroadcast [start v]")
        stmt = scripts[0].body[0]
        assert stmt.block.opcode == "event_broadcast"

    def test_reporter_input_x_position(self):
        """(x position) should be resolved as motion_xposition reporter."""
        scripts = parse("when flag clicked\nmove (x position) steps")
        stmt = scripts[0].body[0]
        steps_input = stmt.block.inputs.get("STEPS")
        assert isinstance(steps_input, ReporterInput)
        assert steps_input.block.opcode == "motion_xposition"

    def test_nested_reporter(self):
        """((x position) + (10)) should produce an operator_add with nested reporter."""
        scripts = parse("when flag clicked\nset [x v] to ((x position) + (10))")
        stmt = scripts[0].body[0]
        value_input = stmt.block.inputs.get("VALUE")
        assert isinstance(value_input, ReporterInput)
        assert value_input.block.opcode == "operator_add"


# ---------------------------------------------------------------------------
# Field resolution
# ---------------------------------------------------------------------------


class TestFieldResolution:
    def test_variable_field(self):
        scripts = parse("when flag clicked\nset [score v] to (0)")
        stmt = scripts[0].body[0]
        assert stmt.block.opcode == "data_setvariableto"
        var_field = stmt.block.fields.get("VARIABLE")
        assert isinstance(var_field, FieldNode)
        assert var_field.value == "score"

    def test_stop_option_field(self):
        scripts = parse("when flag clicked\nstop [all v]")
        stmt = scripts[0].body[0]
        assert stmt.block.opcode == "control_stop"


# ---------------------------------------------------------------------------
# C-blocks (forever, if, repeat)
# ---------------------------------------------------------------------------


class TestCBlocks:
    def test_forever(self):
        source = """when flag clicked
forever
  move (10) steps
end"""
        scripts = parse(source)
        assert len(scripts) == 1
        body = scripts[0].body
        assert len(body) == 1
        stmt = body[0]
        assert stmt.block.opcode == "control_forever"
        assert len(stmt.substacks) == 1
        assert len(stmt.substacks[0]) == 1
        assert stmt.substacks[0][0].block.opcode == "motion_movesteps"

    def test_if_then(self):
        source = """when flag clicked
if <mouse down?> then
  move (10) steps
end"""
        scripts = parse(source)
        stmt = scripts[0].body[0]
        assert stmt.block.opcode == "control_if"
        assert len(stmt.substacks) == 1

    def test_if_else(self):
        source = """when flag clicked
if <mouse down?> then
  move (10) steps
else
  move (-10) steps
end"""
        scripts = parse(source)
        stmt = scripts[0].body[0]
        assert stmt.block.opcode == "control_if_else"
        assert len(stmt.substacks) == 2
        assert len(stmt.substacks[0]) == 1  # if body
        assert len(stmt.substacks[1]) == 1  # else body

    def test_repeat(self):
        source = """when flag clicked
repeat (10)
  move (10) steps
end"""
        scripts = parse(source)
        stmt = scripts[0].body[0]
        assert stmt.block.opcode == "control_repeat"
        assert len(stmt.substacks[0]) == 1

    def test_nested_c_blocks(self):
        source = """when flag clicked
forever
  if <mouse down?> then
    move (10) steps
  end
end"""
        scripts = parse(source)
        forever_stmt = scripts[0].body[0]
        assert forever_stmt.block.opcode == "control_forever"
        inner_if = forever_stmt.substacks[0][0]
        assert inner_if.block.opcode == "control_if"
        assert len(inner_if.substacks[0]) == 1

    def test_unclosed_block_raises(self):
        source = """when flag clicked
forever
  move (10) steps"""
        with pytest.raises(UnclosedBlockError):
            parse(source)

    def test_repeat_until(self):
        source = """when flag clicked
repeat until <mouse down?>
  move (10) steps
end"""
        scripts = parse(source)
        stmt = scripts[0].body[0]
        assert stmt.block.opcode == "control_repeat_until"

    def test_if_with_comparison(self):
        """if <(score) > (10)> then — tests the > inside angle brackets."""
        source = """when flag clicked
if <(score) > (10)> then
  say [Win!]
end"""
        scripts = parse(source)
        stmt = scripts[0].body[0]
        assert stmt.block.opcode == "control_if"
        # The condition should be a ReporterInput with operator_gt
        cond = stmt.block.inputs.get("CONDITION")
        assert isinstance(cond, ReporterInput)
        assert cond.block.opcode == "operator_gt"


# ---------------------------------------------------------------------------
# Custom block definitions
# ---------------------------------------------------------------------------


class TestCustomBlocks:
    def test_simple_define(self):
        source = """define greet (name)
  say [Hello!]
end"""
        scripts = parse(source)
        assert len(scripts) == 1
        assert isinstance(scripts[0], CustomBlockDef)
        custom = scripts[0]
        assert custom.proccode == "greet %s"
        assert custom.argument_names == ["name"]
        assert custom.argument_types == ["s"]
        assert len(custom.body) == 1

    def test_define_multiple_params(self):
        source = """define move to (x) (y)
  set [x v] to (0)
end"""
        scripts = parse(source)
        custom = scripts[0]
        assert custom.proccode == "move to %s %s"
        assert len(custom.argument_names) == 2

    def test_define_boolean_param(self):
        source = """define check <condition>
  show
end"""
        scripts = parse(source)
        custom = scripts[0]
        assert custom.proccode == "check %b"
        assert custom.argument_types == ["b"]

    def test_define_with_body_using_param(self):
        """define block where body uses the parameter."""
        source = """define greet (name)
  say (name) for (2) seconds
end"""
        scripts = parse(source)
        assert isinstance(scripts[0], CustomBlockDef)
        assert len(scripts[0].body) == 1

    def test_unclosed_define_raises(self):
        source = """define myblock (x)
  show"""
        with pytest.raises(UnclosedBlockError):
            parse(source)

    def test_define_followed_by_script(self):
        source = """define greet (name)
  say [Hi!]
end

when flag clicked
show"""
        scripts = parse(source)
        assert len(scripts) == 2
        assert isinstance(scripts[0], CustomBlockDef)
        assert isinstance(scripts[1], ScriptNode)


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestErrors:
    def test_unknown_block_raises(self):
        source = "when flag clicked\nxyzzy plugh"
        with pytest.raises(UnknownBlockError):
            parse(source)

    def test_error_includes_line_number(self):
        source = "when flag clicked\nxyzzy plugh"
        with pytest.raises(UnknownBlockError) as exc_info:
            parse(source)
        assert exc_info.value.line == 2


# ---------------------------------------------------------------------------
# Boolean expressions
# ---------------------------------------------------------------------------


class TestBooleanExpressions:
    def test_mouse_down_boolean(self):
        source = """when flag clicked
if <mouse down?> then
  show
end"""
        scripts = parse(source)
        cond = scripts[0].body[0].block.inputs.get("CONDITION")
        assert isinstance(cond, ReporterInput)
        assert cond.block.opcode == "sensing_mousedown"

    def test_not_boolean(self):
        source = """when flag clicked
if <not <mouse down?>> then
  show
end"""
        scripts = parse(source)
        cond = scripts[0].body[0].block.inputs.get("CONDITION")
        assert isinstance(cond, ReporterInput)
        assert cond.block.opcode == "operator_not"

    def test_and_boolean(self):
        source = """when flag clicked
if <<mouse down?> and <mouse down?>> then
  show
end"""
        scripts = parse(source)
        cond = scripts[0].body[0].block.inputs.get("CONDITION")
        assert isinstance(cond, ReporterInput)
        assert cond.block.opcode == "operator_and"


# ---------------------------------------------------------------------------
# Phase 2: New block parsing
# ---------------------------------------------------------------------------


class TestPhase2Blocks:
    def test_wait_until(self):
        source = """when flag clicked
wait until <mouse down?>"""
        scripts = parse(source)
        stmt = scripts[0].body[0]
        assert stmt.block.opcode == "control_wait_until"
        cond = stmt.block.inputs.get("CONDITION")
        assert isinstance(cond, ReporterInput)
        assert cond.block.opcode == "sensing_mousedown"

    def test_sound_play_until_done(self):
        source = """when flag clicked
play sound [pop v] until done"""
        scripts = parse(source)
        stmt = scripts[0].body[0]
        assert stmt.block.opcode == "sound_playuntildone"

    def test_start_sound(self):
        source = """when flag clicked
start sound [meow v]"""
        scripts = parse(source)
        stmt = scripts[0].body[0]
        assert stmt.block.opcode == "sound_play"

    def test_stop_all_sounds(self):
        source = """when flag clicked
stop all sounds"""
        scripts = parse(source)
        stmt = scripts[0].body[0]
        assert stmt.block.opcode == "sound_stopallsounds"

    def test_clear_graphic_effects(self):
        source = """when flag clicked
clear graphic effects"""
        scripts = parse(source)
        stmt = scripts[0].body[0]
        assert stmt.block.opcode == "looks_cleargraphiceffects"

    def test_next_costume(self):
        source = """when flag clicked
next costume"""
        scripts = parse(source)
        stmt = scripts[0].body[0]
        assert stmt.block.opcode == "looks_nextcostume"

    def test_next_backdrop(self):
        source = """when flag clicked
next backdrop"""
        scripts = parse(source)
        stmt = scripts[0].body[0]
        assert stmt.block.opcode == "looks_nextbackdrop"

    def test_if_on_edge_bounce(self):
        source = """when flag clicked
if on edge, bounce"""
        scripts = parse(source)
        stmt = scripts[0].body[0]
        assert stmt.block.opcode == "motion_ifonedgebounce"

    def test_change_looks_effect(self):
        source = """when flag clicked
change [color v] effect by (25)"""
        scripts = parse(source)
        stmt = scripts[0].body[0]
        assert stmt.block.opcode == "looks_changeeffectby"

    def test_change_sound_effect(self):
        source = """when flag clicked
change [pitch v] sound effect by (10)"""
        scripts = parse(source)
        stmt = scripts[0].body[0]
        assert stmt.block.opcode == "sound_changeeffectby"

    def test_set_volume(self):
        source = """when flag clicked
set volume to (50) %"""
        scripts = parse(source)
        stmt = scripts[0].body[0]
        assert stmt.block.opcode == "sound_setvolumeto"

    def test_clear_sound_effects(self):
        source = """when flag clicked
clear sound effects"""
        scripts = parse(source)
        stmt = scripts[0].body[0]
        assert stmt.block.opcode == "sound_cleareffects"

    def test_show_variable(self):
        source = """when flag clicked
show variable [score v]"""
        scripts = parse(source)
        stmt = scripts[0].body[0]
        assert stmt.block.opcode == "data_showvariable"

    def test_hide_variable(self):
        source = """when flag clicked
hide variable [score v]"""
        scripts = parse(source)
        stmt = scripts[0].body[0]
        assert stmt.block.opcode == "data_hidevariable"

    def test_set_drag_mode(self):
        source = """when flag clicked
set drag mode [draggable v]"""
        scripts = parse(source)
        stmt = scripts[0].body[0]
        assert stmt.block.opcode == "sensing_setdragmode"

    def test_when_key_pressed_hat(self):
        source = """when [space v] key pressed
move (10) steps"""
        scripts = parse(source)
        assert scripts[0].hat.opcode == "event_whenkeypressed"

    def test_set_rotation_style(self):
        source = """when flag clicked
set rotation style [left-right v]"""
        scripts = parse(source)
        stmt = scripts[0].body[0]
        assert stmt.block.opcode == "motion_setrotationstyle"

    def test_go_to_front_layer(self):
        source = """when flag clicked
go to [front v] layer"""
        scripts = parse(source)
        stmt = scripts[0].body[0]
        assert stmt.block.opcode == "looks_gotofrontback"


# ---------------------------------------------------------------------------
# Phase 2: Procedure calls
# ---------------------------------------------------------------------------


class TestProcedureCalls:
    def test_simple_procedure_call(self):
        source = """define greet (name)
  say [Hello!]
end

when flag clicked
greet [World]"""
        scripts = parse(source)
        assert isinstance(scripts[0], CustomBlockDef)
        assert isinstance(scripts[1], ScriptNode)
        stmt = scripts[1].body[0]
        assert stmt.block.opcode == "procedures_call"
        assert stmt.block.mutation is not None
        assert stmt.block.mutation["proccode"] == "greet %s"

    def test_procedure_call_with_paren_arg(self):
        source = """define move by (amount)
  move (10) steps
end

when flag clicked
move by (50)"""
        scripts = parse(source)
        stmt = scripts[1].body[0]
        assert stmt.block.opcode == "procedures_call"
        assert "amount" in stmt.block.inputs

    def test_procedure_call_multi_args(self):
        source = """define go to (x) (y)
  show
end

when flag clicked
go to (100) (200)"""
        scripts = parse(source)
        stmt = scripts[1].body[0]
        assert stmt.block.opcode == "procedures_call"
        assert "x" in stmt.block.inputs
        assert "y" in stmt.block.inputs

    def test_procedure_call_boolean_arg(self):
        source = """define check <condition>
  show
end

when flag clicked
check <mouse down?>"""
        scripts = parse(source)
        stmt = scripts[1].body[0]
        assert stmt.block.opcode == "procedures_call"
        assert "condition" in stmt.block.inputs

    def test_procedure_call_mixed_args(self):
        source = """define draw (size) <filled>
  show
end

when flag clicked
draw (50) <mouse down?>"""
        scripts = parse(source)
        stmt = scripts[1].body[0]
        assert stmt.block.opcode == "procedures_call"
        assert stmt.block.mutation["proccode"] == "draw %s %b"
