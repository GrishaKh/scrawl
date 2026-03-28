"""Tests for the ScratchText code generator."""

from __future__ import annotations

import json
import pytest

from scrawl.compiler import compile_script


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_target(is_stage=True, name="Stage", variables=None, lists=None, broadcasts=None):
    """Create a minimal target dict for testing."""
    return {
        "isStage": is_stage,
        "name": name,
        "variables": variables or {},
        "lists": lists or {},
        "broadcasts": broadcasts or {},
        "blocks": {},
        "comments": {},
        "currentCostume": 0,
        "costumes": [],
        "sounds": [],
        "volume": 100,
        "layerOrder": 0 if is_stage else 1,
    }


def compile_to_blocks(source: str, **kwargs) -> tuple[dict, dict]:
    """Compile source and return (blocks_dict, target_dict)."""
    target = make_target(**kwargs)
    blocks = compile_script(source, target)
    return blocks, target


def find_blocks_by_opcode(blocks: dict, opcode: str) -> list[dict]:
    """Find all blocks with a given opcode."""
    return [b for b in blocks.values() if b["opcode"] == opcode]


# ---------------------------------------------------------------------------
# Basic code generation
# ---------------------------------------------------------------------------


class TestBasicCodeGen:
    def test_hat_block_is_top_level(self):
        blocks, _ = compile_to_blocks("when flag clicked")
        hats = find_blocks_by_opcode(blocks, "event_whenflagclicked")
        assert len(hats) == 1
        assert hats[0]["topLevel"] is True
        assert "x" in hats[0]
        assert "y" in hats[0]

    def test_statement_block_not_top_level(self):
        blocks, _ = compile_to_blocks("when flag clicked\nmove (10) steps")
        moves = find_blocks_by_opcode(blocks, "motion_movesteps")
        assert len(moves) == 1
        assert moves[0]["topLevel"] is False

    def test_next_parent_chaining(self):
        blocks, _ = compile_to_blocks(
            "when flag clicked\nmove (10) steps\nturn right (15) degrees"
        )
        # Find the IDs
        hat_id = None
        move_id = None
        turn_id = None
        for bid, b in blocks.items():
            if b["opcode"] == "event_whenflagclicked":
                hat_id = bid
            elif b["opcode"] == "motion_movesteps":
                move_id = bid
            elif b["opcode"] == "motion_turnright":
                turn_id = bid

        assert hat_id and move_id and turn_id
        assert blocks[hat_id]["next"] == move_id
        assert blocks[move_id]["parent"] == hat_id
        assert blocks[move_id]["next"] == turn_id
        assert blocks[turn_id]["parent"] == move_id
        assert blocks[turn_id]["next"] is None

    def test_blocks_injected_into_target(self):
        target = make_target()
        blocks = compile_script("when flag clicked\nshow", target)
        # Blocks should be in both the return value and the target
        assert len(blocks) > 0
        for bid in blocks:
            assert bid in target["blocks"]


# ---------------------------------------------------------------------------
# Input encoding
# ---------------------------------------------------------------------------


class TestInputEncoding:
    def test_number_input(self):
        blocks, _ = compile_to_blocks("when flag clicked\nmove (10) steps")
        moves = find_blocks_by_opcode(blocks, "motion_movesteps")
        steps = moves[0]["inputs"]["STEPS"]
        # [1, [4, "10"]] — type 1 (literal), code 4 (number)
        assert steps[0] == 1
        assert steps[1][0] == 4
        assert steps[1][1] == "10"

    def test_string_input(self):
        blocks, _ = compile_to_blocks("when flag clicked\nsay [Hello world!]")
        says = find_blocks_by_opcode(blocks, "looks_say")
        msg = says[0]["inputs"]["MESSAGE"]
        # [1, [10, "Hello world!"]] — type 10 (string)
        assert msg[0] == 1
        assert msg[1][0] == 10
        assert msg[1][1] == "Hello world!"

    def test_variable_input_existing_var(self):
        """If a variable exists, codegen should reference it."""
        blocks, target = compile_to_blocks(
            "when flag clicked\nmove (speed) steps",
            variables={"var_speed_id": ["speed", 0]},
        )
        moves = find_blocks_by_opcode(blocks, "motion_movesteps")
        steps = moves[0]["inputs"]["STEPS"]
        # [3, [12, "speed", "var_speed_id"], [10, "0"]]
        assert steps[0] == 3
        assert steps[1][0] == 12
        assert steps[1][1] == "speed"
        assert steps[1][2] == "var_speed_id"

    def test_variable_input_unknown_falls_back(self):
        """If a variable doesn't exist and isn't auto-created, fall back to literal."""
        blocks, target = compile_to_blocks(
            "when flag clicked\nmove (foo) steps"
        )
        moves = find_blocks_by_opcode(blocks, "motion_movesteps")
        steps = moves[0]["inputs"]["STEPS"]
        # Should be a literal since 'foo' is not a known variable
        assert steps[0] == 1  # literal

    def test_reporter_input(self):
        """Nested reporter: set [x v] to ((x position) + (10))."""
        blocks, _ = compile_to_blocks(
            "when flag clicked\nset [x v] to ((x position) + (10))"
        )
        sets = find_blocks_by_opcode(blocks, "data_setvariableto")
        value_input = sets[0]["inputs"]["VALUE"]
        # [3, reporter_id, [10, ""]] — reporter with fallback
        assert value_input[0] == 3
        reporter_id = value_input[1]
        assert isinstance(reporter_id, str)
        assert blocks[reporter_id]["opcode"] == "operator_add"

    def test_boolean_input(self):
        """Boolean input in if block."""
        blocks, _ = compile_to_blocks(
            "when flag clicked\nif <mouse down?> then\n  show\nend"
        )
        ifs = find_blocks_by_opcode(blocks, "control_if")
        cond = ifs[0]["inputs"]["CONDITION"]
        # [2, reporter_id] — boolean reporter
        assert cond[0] == 2
        reporter_id = cond[1]
        assert blocks[reporter_id]["opcode"] == "sensing_mousedown"

    def test_broadcast_input(self):
        blocks, target = compile_to_blocks(
            "when flag clicked\nbroadcast [game start v]"
        )
        bcasts = find_blocks_by_opcode(blocks, "event_broadcast")
        bc_input = bcasts[0]["inputs"]["BROADCAST_INPUT"]
        # [1, [11, "game start", broadcast_id]]
        assert bc_input[0] == 1
        assert bc_input[1][0] == 11
        assert bc_input[1][1] == "game start"


# ---------------------------------------------------------------------------
# Field encoding
# ---------------------------------------------------------------------------


class TestFieldEncoding:
    def test_variable_field_auto_created(self):
        blocks, target = compile_to_blocks(
            "when flag clicked\nset [score v] to (0)"
        )
        sets = find_blocks_by_opcode(blocks, "data_setvariableto")
        var_field = sets[0]["fields"]["VARIABLE"]
        assert var_field[0] == "score"
        # ID should be a non-empty string
        assert isinstance(var_field[1], str) and len(var_field[1]) > 0
        # Variable should be auto-created in target
        assert any(v[0] == "score" for v in target["variables"].values())

    def test_variable_field_existing_var(self):
        blocks, target = compile_to_blocks(
            "when flag clicked\nset [score v] to (0)",
            variables={"existing_id": ["score", 0]},
        )
        sets = find_blocks_by_opcode(blocks, "data_setvariableto")
        var_field = sets[0]["fields"]["VARIABLE"]
        assert var_field[0] == "score"
        assert var_field[1] == "existing_id"

    def test_stop_option_field(self):
        blocks, _ = compile_to_blocks(
            "when flag clicked\nstop [all v]"
        )
        stops = find_blocks_by_opcode(blocks, "control_stop")
        stop_field = stops[0]["fields"]["STOP_OPTION"]
        assert stop_field[0] == "all"
        assert stop_field[1] is None


# ---------------------------------------------------------------------------
# C-block substacks
# ---------------------------------------------------------------------------


class TestSubstacks:
    def test_forever_substack(self):
        blocks, _ = compile_to_blocks(
            "when flag clicked\nforever\n  move (10) steps\nend"
        )
        forevers = find_blocks_by_opcode(blocks, "control_forever")
        assert len(forevers) == 1
        substack = forevers[0]["inputs"].get("SUBSTACK")
        assert substack is not None
        assert substack[0] == 2  # type 2 for block reference
        first_body_id = substack[1]
        assert blocks[first_body_id]["opcode"] == "motion_movesteps"

    def test_if_else_substacks(self):
        source = """when flag clicked
if <mouse down?> then
  show
else
  hide
end"""
        blocks, _ = compile_to_blocks(source)
        ifs = find_blocks_by_opcode(blocks, "control_if_else")
        assert len(ifs) == 1
        # SUBSTACK (if body)
        sub1 = ifs[0]["inputs"]["SUBSTACK"]
        assert sub1[0] == 2
        assert blocks[sub1[1]]["opcode"] == "looks_show"
        # SUBSTACK2 (else body)
        sub2 = ifs[0]["inputs"]["SUBSTACK2"]
        assert sub2[0] == 2
        assert blocks[sub2[1]]["opcode"] == "looks_hide"

    def test_repeat_substack(self):
        blocks, _ = compile_to_blocks(
            "when flag clicked\nrepeat (5)\n  show\nend"
        )
        repeats = find_blocks_by_opcode(blocks, "control_repeat")
        assert len(repeats) == 1
        # Should have TIMES input and SUBSTACK
        assert "TIMES" in repeats[0]["inputs"]
        assert "SUBSTACK" in repeats[0]["inputs"]


# ---------------------------------------------------------------------------
# Custom blocks
# ---------------------------------------------------------------------------


class TestCustomBlockCodeGen:
    def test_custom_block_definition(self):
        source = """define greet (name)
  say [Hello!]
end"""
        blocks, _ = compile_to_blocks(source)

        # Should have procedures_definition (hat)
        defs = find_blocks_by_opcode(blocks, "procedures_definition")
        assert len(defs) == 1
        assert defs[0]["topLevel"] is True

        # Should have procedures_prototype (shadow)
        protos = find_blocks_by_opcode(blocks, "procedures_prototype")
        assert len(protos) == 1
        assert protos[0]["shadow"] is True
        assert "mutation" in protos[0]
        assert protos[0]["mutation"]["proccode"] == "greet %s"

        # Should have argument_reporter_string_number (shadow)
        reporters = find_blocks_by_opcode(blocks, "argument_reporter_string_number")
        assert len(reporters) == 1
        assert reporters[0]["shadow"] is True
        assert reporters[0]["fields"]["VALUE"][0] == "name"

    def test_custom_block_body(self):
        source = """define greet (name)
  say [Hello!]
end"""
        blocks, _ = compile_to_blocks(source)
        defs = find_blocks_by_opcode(blocks, "procedures_definition")
        # Definition hat should chain to the body
        assert defs[0]["next"] is not None
        body_id = defs[0]["next"]
        assert blocks[body_id]["opcode"] == "looks_say"


# ---------------------------------------------------------------------------
# Multiple scripts
# ---------------------------------------------------------------------------


class TestMultipleScripts:
    def test_two_scripts_independent(self):
        source = """when flag clicked
move (10) steps

when this sprite clicked
say [Hi!]"""
        blocks, _ = compile_to_blocks(source, is_stage=False, name="Sprite1")
        hats = [b for b in blocks.values() if b["topLevel"]]
        assert len(hats) == 2

    def test_broadcast_auto_creation(self):
        source = """when flag clicked
broadcast [start v]

when I receive [start v]
show"""
        blocks, target = compile_to_blocks(source)
        # Broadcast should be created
        assert len(target["broadcasts"]) >= 1
        bc_name = list(target["broadcasts"].values())[0]
        assert bc_name == "start"


# ---------------------------------------------------------------------------
# Block structure validation
# ---------------------------------------------------------------------------


class TestBlockStructure:
    def test_all_blocks_have_required_fields(self):
        """Every generated block should have the required Scratch fields."""
        source = """when flag clicked
set [score v] to (0)
forever
  change [score v] by (1)
  if <(score) > (10)> then
    say [Win!]
  end
end"""
        blocks, _ = compile_to_blocks(source)
        required_keys = {"opcode", "next", "parent", "inputs", "fields", "shadow", "topLevel"}
        for bid, block in blocks.items():
            for key in required_keys:
                assert key in block, f"Block {bid} ({block['opcode']}) missing key '{key}'"

    def test_shadow_blocks_marked_correctly(self):
        """Shadow blocks should have shadow=True, others shadow=False."""
        source = """define myblock (x)
  show
end"""
        blocks, _ = compile_to_blocks(source)
        for bid, block in blocks.items():
            if block["opcode"] in ("procedures_prototype", "argument_reporter_string_number"):
                assert block["shadow"] is True, f"{block['opcode']} should be shadow"
            elif block["opcode"] == "procedures_definition":
                assert block["shadow"] is False

    def test_no_orphan_blocks(self):
        """All non-top-level blocks should have a parent."""
        source = """when flag clicked
move (10) steps
turn right (15) degrees"""
        blocks, _ = compile_to_blocks(source)
        for bid, block in blocks.items():
            if not block["topLevel"]:
                assert block["parent"] is not None, f"Block {bid} ({block['opcode']}) is orphaned"
                assert block["parent"] in blocks, f"Block {bid} has invalid parent"


# ---------------------------------------------------------------------------
# Phase 2: New block codegen
# ---------------------------------------------------------------------------


class TestPhase2CodeGen:
    def test_sound_play_until_done(self):
        blocks, _ = compile_to_blocks(
            "when flag clicked\nplay sound [pop v] until done"
        )
        sounds = find_blocks_by_opcode(blocks, "sound_playuntildone")
        assert len(sounds) == 1
        # Should have a menu shadow block
        assert "SOUND_MENU" in sounds[0]["inputs"]

    def test_set_volume(self):
        blocks, _ = compile_to_blocks(
            "when flag clicked\nset volume to (50) %"
        )
        vols = find_blocks_by_opcode(blocks, "sound_setvolumeto")
        assert len(vols) == 1
        assert "VOLUME" in vols[0]["inputs"]

    def test_volume_reporter(self):
        blocks, _ = compile_to_blocks(
            "when flag clicked\nset [x v] to (volume)"
        )
        # volume should be resolved as a reporter
        vols = find_blocks_by_opcode(blocks, "sound_volume")
        assert len(vols) == 1

    def test_clear_graphic_effects(self):
        blocks, _ = compile_to_blocks(
            "when flag clicked\nclear graphic effects"
        )
        clears = find_blocks_by_opcode(blocks, "looks_cleargraphiceffects")
        assert len(clears) == 1
        # No inputs or fields for this block
        assert clears[0]["inputs"] == {}

    def test_costume_number_default_field(self):
        """costume number should have NUMBER_NAME field = 'number'."""
        blocks, _ = compile_to_blocks(
            "when flag clicked\nset [x v] to (costume number)"
        )
        costumes = find_blocks_by_opcode(blocks, "looks_costumenumbername")
        assert len(costumes) == 1
        assert "NUMBER_NAME" in costumes[0]["fields"]
        assert costumes[0]["fields"]["NUMBER_NAME"][0] == "number"

    def test_costume_name_default_field(self):
        """costume name should have NUMBER_NAME field = 'name'."""
        blocks, _ = compile_to_blocks(
            "when flag clicked\nset [x v] to (costume name)"
        )
        costumes = find_blocks_by_opcode(blocks, "looks_costumenumbername")
        assert len(costumes) == 1
        assert costumes[0]["fields"]["NUMBER_NAME"][0] == "name"

    def test_wait_until_codegen(self):
        blocks, _ = compile_to_blocks(
            "when flag clicked\nwait until <mouse down?>"
        )
        waits = find_blocks_by_opcode(blocks, "control_wait_until")
        assert len(waits) == 1
        assert "CONDITION" in waits[0]["inputs"]
        # Boolean input type
        cond = waits[0]["inputs"]["CONDITION"]
        assert cond[0] == 2  # boolean reporter

    def test_motion_goto_menu(self):
        """go to [random position v] should have a menu shadow."""
        blocks, _ = compile_to_blocks(
            "when flag clicked\ngo to [random position v]"
        )
        gotos = find_blocks_by_opcode(blocks, "motion_goto")
        assert len(gotos) == 1
        # Should have TO input pointing to menu shadow
        assert "TO" in gotos[0]["inputs"]
        menu_id = gotos[0]["inputs"]["TO"][1]
        assert blocks[menu_id]["opcode"] == "motion_goto_menu"

    def test_change_looks_effect(self):
        blocks, _ = compile_to_blocks(
            "when flag clicked\nchange [color v] effect by (25)"
        )
        effects = find_blocks_by_opcode(blocks, "looks_changeeffectby")
        assert len(effects) == 1
        assert "CHANGE" in effects[0]["inputs"]
        assert "EFFECT" in effects[0]["fields"]
        assert effects[0]["fields"]["EFFECT"][0] == "color"

    def test_change_sound_effect(self):
        blocks, _ = compile_to_blocks(
            "when flag clicked\nchange [pitch v] sound effect by (10)"
        )
        effects = find_blocks_by_opcode(blocks, "sound_changeeffectby")
        assert len(effects) == 1
        assert "VALUE" in effects[0]["inputs"]
        assert "EFFECT" in effects[0]["fields"]
        assert effects[0]["fields"]["EFFECT"][0] == "pitch"

    def test_show_variable(self):
        blocks, _ = compile_to_blocks(
            "when flag clicked\nshow variable [score v]"
        )
        shows = find_blocks_by_opcode(blocks, "data_showvariable")
        assert len(shows) == 1
        assert "VARIABLE" in shows[0]["fields"]

    def test_if_on_edge_bounce(self):
        blocks, _ = compile_to_blocks(
            "when flag clicked\nif on edge, bounce"
        )
        bounces = find_blocks_by_opcode(blocks, "motion_ifonedgebounce")
        assert len(bounces) == 1

    def test_set_rotation_style(self):
        blocks, _ = compile_to_blocks(
            "when flag clicked\nset rotation style [left-right v]"
        )
        styles = find_blocks_by_opcode(blocks, "motion_setrotationstyle")
        assert len(styles) == 1
        assert "STYLE" in styles[0]["fields"]
        assert styles[0]["fields"]["STYLE"][0] == "left-right"


# ---------------------------------------------------------------------------
# Phase 2: Procedure call codegen
# ---------------------------------------------------------------------------


class TestProcedureCallCodeGen:
    def test_procedure_call_generates_mutation(self):
        source = """define greet (name)
  say [Hello!]
end

when flag clicked
greet [World]"""
        blocks, _ = compile_to_blocks(source)
        calls = find_blocks_by_opcode(blocks, "procedures_call")
        assert len(calls) == 1
        assert "mutation" in calls[0]
        assert calls[0]["mutation"]["proccode"] == "greet %s"
        assert calls[0]["mutation"]["tagName"] == "mutation"

    def test_procedure_call_has_inputs(self):
        source = """define move by (amount)
  move (10) steps
end

when flag clicked
move by (50)"""
        blocks, _ = compile_to_blocks(source)
        calls = find_blocks_by_opcode(blocks, "procedures_call")
        assert len(calls) == 1
        assert "amount" in calls[0]["inputs"]
        # Input should encode the literal 50
        amount_input = calls[0]["inputs"]["amount"]
        assert amount_input[1][1] == "50"

    def test_procedure_call_chained(self):
        """Procedure call should chain with next/parent like normal blocks."""
        source = """define greet (name)
  say [Hello!]
end

when flag clicked
greet [World]
show"""
        blocks, _ = compile_to_blocks(source)
        calls = find_blocks_by_opcode(blocks, "procedures_call")
        assert len(calls) == 1
        # Should have a next block
        assert calls[0]["next"] is not None
        next_id = calls[0]["next"]
        assert blocks[next_id]["opcode"] == "looks_show"
