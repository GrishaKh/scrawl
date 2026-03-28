"""Tests for the decompiler — block JSON to .scr text."""

from __future__ import annotations

import pytest

from scrawl.compiler import compile_script
from scrawl.decompiler import decompile_target
from scrawl.generate import create_project, add_sprite
from scrawl.model import ScratchProject


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def round_trip(source: str, with_sprite: bool = False) -> str:
    """Compile source → blocks → decompile back to text."""
    data, assets = create_project()
    if with_sprite:
        add_sprite(data, "Cat")
    project = ScratchProject(data)
    target = data["targets"][1 if with_sprite else 0]
    compile_script(source, target, project)
    return decompile_target(target)


# ---------------------------------------------------------------------------
# Basic round-trip tests
# ---------------------------------------------------------------------------


class TestBasicRoundTrip:
    def test_simple_script(self):
        source = "when flag clicked\nmove (10) steps\n"
        result = round_trip(source, with_sprite=True)
        assert "when flag clicked" in result
        assert "move (10) steps" in result

    def test_multiple_statements(self):
        source = "when flag clicked\nmove (10) steps\nturn right (15) degrees\nshow\n"
        result = round_trip(source, with_sprite=True)
        assert "move (10) steps" in result
        assert "turn right (15) degrees" in result
        assert "show" in result

    def test_say_with_string(self):
        source = "when flag clicked\nsay [Hello world!]\n"
        result = round_trip(source)
        assert "say [Hello world!]" in result

    def test_say_for_secs(self):
        source = "when flag clicked\nsay [Hi!] for (2) seconds\n"
        result = round_trip(source)
        assert "say [Hi!] for (2) seconds" in result

    def test_set_variable(self):
        source = "when flag clicked\nset [score v] to (0)\n"
        result = round_trip(source)
        assert "set [score v] to (0)" in result

    def test_change_variable(self):
        source = "when flag clicked\nchange [score v] by (1)\n"
        result = round_trip(source)
        assert "change [score v] by (1)" in result

    def test_broadcast(self):
        source = "when flag clicked\nbroadcast [start v]\n"
        result = round_trip(source)
        assert "broadcast [start v]" in result


# ---------------------------------------------------------------------------
# C-block round-trips
# ---------------------------------------------------------------------------


class TestCBlockRoundTrip:
    def test_forever(self):
        source = "when flag clicked\nforever\n  move (10) steps\nend\n"
        result = round_trip(source, with_sprite=True)
        assert "forever" in result
        assert "  move (10) steps" in result
        assert "end" in result

    def test_repeat(self):
        source = "when flag clicked\nrepeat (10)\n  show\nend\n"
        result = round_trip(source)
        assert "repeat (10)" in result
        assert "  show" in result
        assert "end" in result

    def test_if_then(self):
        source = "when flag clicked\nif <mouse down?> then\n  show\nend\n"
        result = round_trip(source)
        assert "if <mouse down?> then" in result
        assert "  show" in result

    def test_if_else(self):
        source = "when flag clicked\nif <mouse down?> then\n  show\nelse\n  hide\nend\n"
        result = round_trip(source)
        assert "if <mouse down?> then" in result
        assert "  show" in result
        assert "else" in result
        assert "  hide" in result

    def test_nested_c_blocks(self):
        source = (
            "when flag clicked\nforever\n  if <mouse down?> then\n"
            "    move (10) steps\n  end\nend\n"
        )
        result = round_trip(source, with_sprite=True)
        assert "forever" in result
        assert "  if <mouse down?> then" in result
        assert "    move (10) steps" in result

    def test_repeat_until(self):
        source = "when flag clicked\nrepeat until <mouse down?>\n  move (1) steps\nend\n"
        result = round_trip(source, with_sprite=True)
        assert "repeat until <mouse down?>" in result

    def test_wait_until(self):
        source = "when flag clicked\nwait until <mouse down?>\n"
        result = round_trip(source)
        assert "wait until <mouse down?>" in result


# ---------------------------------------------------------------------------
# Reporter and operator round-trips
# ---------------------------------------------------------------------------


class TestReporterRoundTrip:
    def test_nested_operator(self):
        source = "when flag clicked\nset [x v] to ((1) + (2))\n"
        result = round_trip(source)
        assert "((1) + (2))" in result

    def test_comparison_in_if(self):
        source = "when flag clicked\nif <(score) > (10)> then\n  show\nend\n"
        result = round_trip(source)
        assert "(score) > (10)" in result

    def test_boolean_not(self):
        source = "when flag clicked\nif <not <mouse down?>> then\n  show\nend\n"
        result = round_trip(source)
        assert "not <mouse down?>" in result

    def test_boolean_and(self):
        source = "when flag clicked\nif <<mouse down?> and <mouse down?>> then\n  show\nend\n"
        result = round_trip(source)
        assert "<mouse down?> and <mouse down?>" in result


# ---------------------------------------------------------------------------
# Hat blocks
# ---------------------------------------------------------------------------


class TestHatBlocks:
    def test_when_flag_clicked(self):
        result = round_trip("when flag clicked\nshow\n")
        assert result.startswith("when flag clicked")

    def test_when_key_pressed(self):
        result = round_trip("when [space v] key pressed\nshow\n")
        assert "when [space v] key pressed" in result

    def test_when_receive(self):
        result = round_trip("when I receive [start v]\nshow\n")
        assert "when I receive [start v]" in result

    def test_when_sprite_clicked(self):
        result = round_trip("when this sprite clicked\nshow\n", with_sprite=True)
        assert "when this sprite clicked" in result


# ---------------------------------------------------------------------------
# Phase 2 blocks
# ---------------------------------------------------------------------------


class TestPhase2Decompile:
    def test_sound_blocks(self):
        source = "when flag clicked\nplay sound [pop v] until done\nstop all sounds\n"
        result = round_trip(source)
        assert "play sound [pop v] until done" in result
        assert "stop all sounds" in result

    def test_set_volume(self):
        result = round_trip("when flag clicked\nset volume to (50) %\n")
        assert "set volume to (50) %" in result

    def test_clear_effects(self):
        result = round_trip("when flag clicked\nclear graphic effects\nclear sound effects\n")
        assert "clear graphic effects" in result
        assert "clear sound effects" in result

    def test_if_on_edge_bounce(self):
        result = round_trip("when flag clicked\nif on edge, bounce\n", with_sprite=True)
        assert "if on edge, bounce" in result

    def test_go_to_menu(self):
        result = round_trip("when flag clicked\ngo to [random position v]\n", with_sprite=True)
        assert "go to [random position v]" in result

    def test_set_rotation_style(self):
        result = round_trip(
            "when flag clicked\nset rotation style [left-right v]\n",
            with_sprite=True,
        )
        assert "set rotation style [left-right v]" in result

    def test_change_effect(self):
        result = round_trip("when flag clicked\nchange [color v] effect by (25)\n")
        assert "change [color v] effect by (25)" in result

    def test_show_variable(self):
        result = round_trip("when flag clicked\nshow variable [score v]\n")
        assert "show variable [score v]" in result


# ---------------------------------------------------------------------------
# Custom blocks
# ---------------------------------------------------------------------------


class TestCustomBlockDecompile:
    def test_simple_define(self):
        source = "define greet (name)\n  say [Hello!]\nend\n"
        result = round_trip(source)
        assert "define greet (name)" in result
        assert "  say [Hello!]" in result
        assert "end" in result

    def test_define_with_boolean(self):
        source = "define check <condition>\n  show\nend\n"
        result = round_trip(source)
        assert "define check <condition>" in result

    def test_procedure_call(self):
        source = "define greet (name)\n  say [Hello!]\nend\n\nwhen flag clicked\ngreet [World]\n"
        result = round_trip(source)
        assert "define greet (name)" in result
        # The call should appear
        assert "greet" in result.split("when flag clicked")[1]

    def test_procedure_call_multi_args(self):
        source = (
            "define go to (x) (y)\n  show\nend\n\n"
            "when flag clicked\ngo to (100) (200)\n"
        )
        result = round_trip(source)
        assert "define go to (x) (y)" in result


# ---------------------------------------------------------------------------
# Multiple scripts
# ---------------------------------------------------------------------------


class TestMultipleScripts:
    def test_two_scripts(self):
        source = (
            "when flag clicked\nshow\n\n"
            "when this sprite clicked\nhide\n"
        )
        result = round_trip(source, with_sprite=True)
        assert "when flag clicked" in result
        assert "when this sprite clicked" in result
        assert "show" in result
        assert "hide" in result

    def test_empty_target(self):
        data, _ = create_project()
        result = decompile_target(data["targets"][0])
        assert result == ""


# ---------------------------------------------------------------------------
# CLI integration
# ---------------------------------------------------------------------------


class TestDecompileCLI:
    def test_decompile_to_stdout(self, tmp_path, capsys):
        from scrawl.cli import main
        from scrawl.generate import write_project

        data, assets = create_project()
        project = ScratchProject(data)
        target = data["targets"][0]
        compile_script("when flag clicked\nsay [Hello!]\n", target, project)
        write_project(data, assets, tmp_path / "proj")

        result = main(["decompile", str(tmp_path / "proj"), "--target", "Stage"])
        assert result == 0
        output = capsys.readouterr().out
        assert "when flag clicked" in output
        assert "say [Hello!]" in output

    def test_decompile_to_file(self, tmp_path):
        from scrawl.cli import main
        from scrawl.generate import write_project

        data, assets = create_project()
        project = ScratchProject(data)
        target = data["targets"][0]
        compile_script("when flag clicked\nshow\n", target, project)
        write_project(data, assets, tmp_path / "proj")

        out_file = tmp_path / "output.scr"
        result = main([
            "decompile", str(tmp_path / "proj"),
            "--target", "Stage",
            "--output", str(out_file),
        ])
        assert result == 0
        assert out_file.exists()
        content = out_file.read_text()
        assert "when flag clicked" in content

    def test_decompile_all_targets(self, tmp_path, capsys):
        from scrawl.cli import main
        from scrawl.generate import write_project

        data, assets = create_project()
        assets.update(add_sprite(data, "Cat"))
        project = ScratchProject(data)
        compile_script("when flag clicked\nshow\n", data["targets"][0], project)
        compile_script("when flag clicked\nhide\n", data["targets"][1], project)
        write_project(data, assets, tmp_path / "proj")

        result = main(["decompile", str(tmp_path / "proj")])
        assert result == 0
        output = capsys.readouterr().out
        assert "=== Stage ===" in output
        assert "=== Cat ===" in output
