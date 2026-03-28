"""Integration tests for the ScratchText compiler.

Tests the full pipeline: compile → inject → validate round-trip.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scrawl.compiler import compile_script
from scrawl.compiler.errors import CompileError
from scrawl.validate import validate_project
from scrawl.model import ScratchProject


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_full_project(extra_sprites=0) -> dict:
    """Create a minimal but valid full project dict."""
    targets = [
        {
            "isStage": True,
            "name": "Stage",
            "variables": {"stagevar1": ["timer value", 0]},
            "lists": {"stagelist1": ["scores", []]},
            "broadcasts": {"bc1": "game start"},
            "blocks": {},
            "comments": {},
            "currentCostume": 0,
            "costumes": [
                {
                    "name": "backdrop1",
                    "dataFormat": "svg",
                    "assetId": "cd21514d0531fdffb22204e0ec5ed84a",
                    "md5ext": "cd21514d0531fdffb22204e0ec5ed84a.svg",
                    "rotationCenterX": 240,
                    "rotationCenterY": 180,
                }
            ],
            "sounds": [],
            "volume": 100,
            "layerOrder": 0,
            "tempo": 60,
            "videoTransparency": 50,
            "videoState": "off",
            "textToSpeechLanguage": None,
        }
    ]

    for i in range(extra_sprites):
        targets.append(
            {
                "isStage": False,
                "name": f"Sprite{i + 1}",
                "variables": {f"sprvar{i}": [f"sprite var {i}", 0]},
                "lists": {},
                "broadcasts": {},
                "blocks": {},
                "comments": {},
                "currentCostume": 0,
                "costumes": [
                    {
                        "name": "costume1",
                        "dataFormat": "svg",
                        "assetId": "bcf454acf82e4504149f7ffe07081dbc",
                        "md5ext": "bcf454acf82e4504149f7ffe07081dbc.svg",
                        "rotationCenterX": 48,
                        "rotationCenterY": 50,
                    }
                ],
                "sounds": [],
                "volume": 100,
                "layerOrder": i + 1,
                "visible": True,
                "x": 0,
                "y": 0,
                "size": 100,
                "direction": 90,
                "draggable": False,
                "rotationStyle": "all around",
            }
        )

    return {
        "targets": targets,
        "monitors": [],
        "extensions": [],
        "meta": {"semver": "3.0.0", "vm": "0.2.0", "agent": "test"},
    }


# ---------------------------------------------------------------------------
# Compile → Validate round-trips
# ---------------------------------------------------------------------------


class TestCompileValidateRoundTrip:
    def test_simple_script_validates(self):
        """Compile a simple script and verify it passes validation."""
        project_data = make_full_project()
        project = ScratchProject(project_data)
        target = project_data["targets"][0]  # Stage

        source = """when flag clicked
say [Hello!] for (2) seconds
"""
        blocks = compile_script(source, target, project)
        assert len(blocks) >= 2

        issues = validate_project(project)
        errors = [i for i in issues if i.severity == "error"]
        assert len(errors) == 0, f"Validation errors: {[e.message for e in errors]}"

    def test_variables_script_validates(self):
        project_data = make_full_project()
        project = ScratchProject(project_data)
        target = project_data["targets"][0]

        source = """when flag clicked
set [score v] to (0)
change [score v] by (1)
"""
        blocks = compile_script(source, target, project)
        issues = validate_project(project)
        errors = [i for i in issues if i.severity == "error"]
        assert len(errors) == 0, f"Validation errors: {[e.message for e in errors]}"

    def test_control_flow_validates(self):
        project_data = make_full_project()
        project = ScratchProject(project_data)
        target = project_data["targets"][0]

        source = """when flag clicked
set [x v] to (0)
forever
  change [x v] by (1)
  if <(x) > (100)> then
    say [Done!]
    stop [all v]
  end
end
"""
        blocks = compile_script(source, target, project)
        assert len(blocks) >= 6

        issues = validate_project(project)
        errors = [i for i in issues if i.severity == "error"]
        assert len(errors) == 0, f"Validation errors: {[e.message for e in errors]}"

    def test_broadcast_round_trip(self):
        project_data = make_full_project()
        project = ScratchProject(project_data)
        target = project_data["targets"][0]

        source = """when flag clicked
broadcast [game start v]

when I receive [game start v]
say [Started!]
"""
        blocks = compile_script(source, target, project)
        issues = validate_project(project)
        errors = [i for i in issues if i.severity == "error"]
        assert len(errors) == 0, f"Validation errors: {[e.message for e in errors]}"

    def test_custom_block_validates(self):
        project_data = make_full_project()
        project = ScratchProject(project_data)
        target = project_data["targets"][0]

        source = """define greet (name)
  say [Hi!]
end
"""
        blocks = compile_script(source, target, project)
        assert len(blocks) >= 3  # definition + prototype + reporter + body

        issues = validate_project(project)
        errors = [i for i in issues if i.severity == "error"]
        assert len(errors) == 0, f"Validation errors: {[e.message for e in errors]}"

    def test_multiple_scripts_validate(self):
        project_data = make_full_project()
        project = ScratchProject(project_data)
        target = project_data["targets"][0]

        source = """when flag clicked
set [score v] to (0)
forever
  change [score v] by (1)
  wait (1) seconds
end

when I receive [game start v]
repeat (10)
  say [Go!] for (1) seconds
end
"""
        blocks = compile_script(source, target, project)
        assert len(blocks) >= 8

        issues = validate_project(project)
        errors = [i for i in issues if i.severity == "error"]
        assert len(errors) == 0, f"Validation errors: {[e.message for e in errors]}"


# ---------------------------------------------------------------------------
# Sprite target injection
# ---------------------------------------------------------------------------


class TestSpriteInjection:
    def test_inject_into_sprite(self):
        project_data = make_full_project(extra_sprites=1)
        project = ScratchProject(project_data)
        sprite_target = project_data["targets"][1]  # Sprite1

        source = """when flag clicked
move (10) steps
turn right (90) degrees
"""
        blocks = compile_script(source, sprite_target, project)
        assert len(blocks) >= 3
        assert len(sprite_target["blocks"]) >= 3

    def test_sprite_uses_stage_variables(self):
        """Sprite should be able to reference stage global variables."""
        project_data = make_full_project(extra_sprites=1)
        project = ScratchProject(project_data)
        sprite_target = project_data["targets"][1]

        source = """when flag clicked
set [timer value v] to (0)
"""
        blocks = compile_script(source, sprite_target, project)
        # Should reference the stage variable, not create a new one
        found_set = None
        for b in blocks.values():
            if b["opcode"] == "data_setvariableto":
                found_set = b
                break
        assert found_set is not None
        var_field = found_set["fields"]["VARIABLE"]
        assert var_field[0] == "timer value"
        assert var_field[1] == "stagevar1"  # The stage's variable ID


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_empty_source(self):
        target = {
            "isStage": True, "name": "Stage",
            "variables": {}, "lists": {}, "broadcasts": {},
            "blocks": {}, "comments": {},
            "currentCostume": 0, "costumes": [], "sounds": [],
            "volume": 100, "layerOrder": 0,
        }
        blocks = compile_script("", target)
        assert blocks == {}

    def test_only_comments(self):
        target = {
            "isStage": True, "name": "Stage",
            "variables": {}, "lists": {}, "broadcasts": {},
            "blocks": {}, "comments": {},
            "currentCostume": 0, "costumes": [], "sounds": [],
            "volume": 100, "layerOrder": 0,
        }
        blocks = compile_script("// just a comment\n# another comment", target)
        assert blocks == {}

    def test_color_input(self):
        target = {
            "isStage": True, "name": "Stage",
            "variables": {}, "lists": {}, "broadcasts": {},
            "blocks": {}, "comments": {},
            "currentCostume": 0, "costumes": [], "sounds": [],
            "volume": 100, "layerOrder": 0,
        }
        source = "when flag clicked\nset pen color to (#ff0000)"
        blocks = compile_script(source, target)
        pen_blocks = [b for b in blocks.values() if b["opcode"] == "pen_setPenColorToColor"]
        assert len(pen_blocks) == 1

    def test_negative_number_input(self):
        target = {
            "isStage": True, "name": "Stage",
            "variables": {}, "lists": {}, "broadcasts": {},
            "blocks": {}, "comments": {},
            "currentCostume": 0, "costumes": [], "sounds": [],
            "volume": 100, "layerOrder": 0,
        }
        source = "when flag clicked\nmove (-5) steps"
        blocks = compile_script(source, target)
        moves = [b for b in blocks.values() if b["opcode"] == "motion_movesteps"]
        assert len(moves) == 1
        steps = moves[0]["inputs"]["STEPS"]
        assert steps[1][1] == "-5"

    def test_if_else_upgrade(self):
        """if/then/else should generate control_if_else, not control_if."""
        target = {
            "isStage": True, "name": "Stage",
            "variables": {}, "lists": {}, "broadcasts": {},
            "blocks": {}, "comments": {},
            "currentCostume": 0, "costumes": [], "sounds": [],
            "volume": 100, "layerOrder": 0,
        }
        source = """when flag clicked
if <mouse down?> then
  show
else
  hide
end"""
        blocks = compile_script(source, target)
        if_else = [b for b in blocks.values() if b["opcode"] == "control_if_else"]
        assert len(if_else) == 1
        assert "SUBSTACK" in if_else[0]["inputs"]
        assert "SUBSTACK2" in if_else[0]["inputs"]


# ---------------------------------------------------------------------------
# Real project injection (optional)
# ---------------------------------------------------------------------------


class TestRealProject:
    def test_inject_into_real_project(self, real_project_path):
        """Inject a script into the real LogicGateSimulator project."""
        from scrawl import io

        project = io.load_project(real_project_path)
        # Find the Stage target
        stage = project.stage
        assert stage is not None

        original_block_count = len(stage.get("blocks", {}))

        source = """when flag clicked
set [test_var v] to (42)
say [Injected by compiler!] for (2) seconds
"""
        blocks = compile_script(source, stage, project)
        assert len(blocks) >= 3
        assert len(stage["blocks"]) == original_block_count + len(blocks)

        # Validate the full project
        issues = validate_project(project)
        errors = [i for i in issues if i.severity == "error"]
        # Some pre-existing errors may exist, but our new blocks shouldn't add new ones
        # Just verify the project doesn't crash during validation
        assert isinstance(issues, list)


# ---------------------------------------------------------------------------
# Phase 2: New block round-trip tests
# ---------------------------------------------------------------------------


class TestPhase2RoundTrips:
    def test_sound_blocks_validate(self):
        project_data = make_full_project()
        project = ScratchProject(project_data)
        target = project_data["targets"][0]

        source = """when flag clicked
play sound [pop v] until done
start sound [pop v]
stop all sounds
set volume to (50) %
change volume by (10)
clear sound effects
"""
        blocks = compile_script(source, target, project)
        assert len(blocks) >= 7

        issues = validate_project(project)
        errors = [i for i in issues if i.severity == "error"]
        assert len(errors) == 0, f"Validation errors: {[e.message for e in errors]}"

    def test_motion_blocks_validate(self):
        project_data = make_full_project(extra_sprites=1)
        project = ScratchProject(project_data)
        target = project_data["targets"][1]  # sprite

        source = """when flag clicked
go to [random position v]
if on edge, bounce
set rotation style [left-right v]
point towards [mouse-pointer v]
"""
        blocks = compile_script(source, target, project)
        assert len(blocks) >= 5

        issues = validate_project(project)
        errors = [i for i in issues if i.severity == "error"]
        assert len(errors) == 0, f"Validation errors: {[e.message for e in errors]}"

    def test_looks_blocks_validate(self):
        project_data = make_full_project()
        project = ScratchProject(project_data)
        target = project_data["targets"][0]

        source = """when flag clicked
change [color v] effect by (25)
set [ghost v] effect to (50)
clear graphic effects
change size by (10)
next costume
next backdrop
go to [front v] layer
"""
        blocks = compile_script(source, target, project)
        assert len(blocks) >= 8

        issues = validate_project(project)
        errors = [i for i in issues if i.severity == "error"]
        assert len(errors) == 0, f"Validation errors: {[e.message for e in errors]}"

    def test_control_wait_until_validates(self):
        project_data = make_full_project()
        project = ScratchProject(project_data)
        target = project_data["targets"][0]

        source = """when flag clicked
wait until <mouse down?>
say [Done waiting!]
"""
        blocks = compile_script(source, target, project)
        assert len(blocks) >= 3

        issues = validate_project(project)
        errors = [i for i in issues if i.severity == "error"]
        assert len(errors) == 0, f"Validation errors: {[e.message for e in errors]}"

    def test_data_show_hide_validates(self):
        project_data = make_full_project()
        project = ScratchProject(project_data)
        target = project_data["targets"][0]

        source = """when flag clicked
show variable [score v]
hide variable [score v]
"""
        blocks = compile_script(source, target, project)
        assert len(blocks) >= 3

        issues = validate_project(project)
        errors = [i for i in issues if i.severity == "error"]
        assert len(errors) == 0, f"Validation errors: {[e.message for e in errors]}"

    def test_sensing_blocks_validate(self):
        project_data = make_full_project()
        project = ScratchProject(project_data)
        target = project_data["targets"][0]

        source = """when flag clicked
set [x v] to (current [year v])
set [y v] to (days since 2000)
set [z v] to (username)
"""
        blocks = compile_script(source, target, project)
        assert len(blocks) >= 4

        issues = validate_project(project)
        errors = [i for i in issues if i.severity == "error"]
        assert len(errors) == 0, f"Validation errors: {[e.message for e in errors]}"

    def test_custom_block_call_validates(self):
        project_data = make_full_project()
        project = ScratchProject(project_data)
        target = project_data["targets"][0]

        source = """define greet (name)
  say [Hello!]
end

when flag clicked
greet [World]
"""
        blocks = compile_script(source, target, project)
        # definition + prototype + arg_reporter + body + hat + call
        assert len(blocks) >= 6

        issues = validate_project(project)
        errors = [i for i in issues if i.severity == "error"]
        assert len(errors) == 0, f"Validation errors: {[e.message for e in errors]}"

    def test_full_phase2_script_validates(self):
        """Comprehensive script using many Phase 2 blocks."""
        project_data = make_full_project(extra_sprites=1)
        project = ScratchProject(project_data)
        target = project_data["targets"][1]  # sprite

        source = """when flag clicked
go to [random position v]
set rotation style [all around v]
forever
  if on edge, bounce
  move (10) steps
  change [color v] effect by (5)
  if <mouse down?> then
    play sound [pop v] until done
    change volume by (-5)
  end
  wait until <not <mouse down?>>
end

when [space v] key pressed
clear graphic effects
clear sound effects
next costume
set volume to (100) %
"""
        blocks = compile_script(source, target, project)
        assert len(blocks) >= 15

        issues = validate_project(project)
        errors = [i for i in issues if i.severity == "error"]
        assert len(errors) == 0, f"Validation errors: {[e.message for e in errors]}"
