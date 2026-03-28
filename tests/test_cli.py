"""Integration tests for scrawl.cli — full CLI commands."""

import json
import pytest

from scrawl.cli import main


class TestHelp:
    def test_help_returns_1_no_args(self, capsys):
        result = main([])
        assert result == 1

    def test_version(self, capsys):
        with pytest.raises(SystemExit) as exc:
            main(["--version"])
        assert exc.value.code == 0


class TestInfoCommand:
    def test_info_directory(self, minimal_project_dir, capsys):
        result = main(["info", str(minimal_project_dir)])
        assert result == 0
        output = capsys.readouterr().out
        assert "Sprites:" in output
        assert "1" in output

    def test_info_json(self, minimal_project_dir, capsys):
        result = main(["info", str(minimal_project_dir), "--json"])
        assert result == 0
        data = json.loads(capsys.readouterr().out)
        assert data["sprite_count"] == 1

    def test_info_sb3(self, minimal_sb3, capsys):
        result = main(["info", str(minimal_sb3)])
        assert result == 0


class TestSpritesCommand:
    def test_sprites(self, minimal_project_dir, capsys):
        result = main(["sprites", str(minimal_project_dir)])
        assert result == 0
        output = capsys.readouterr().out
        assert "Sprite1" in output
        assert "Stage" in output


class TestVariablesCommand:
    def test_variables(self, minimal_project_dir, capsys):
        result = main(["variables", str(minimal_project_dir)])
        assert result == 0
        output = capsys.readouterr().out
        assert "my variable" in output


class TestBlocksCommand:
    def test_blocks(self, minimal_project_dir, capsys):
        result = main(["blocks", str(minimal_project_dir)])
        assert result == 0
        output = capsys.readouterr().out
        assert "Total blocks:" in output


class TestAssetsCommand:
    def test_assets(self, minimal_project_dir, capsys):
        result = main(["assets", str(minimal_project_dir)])
        assert result == 0
        output = capsys.readouterr().out
        assert ".svg" in output


class TestTreeCommand:
    def test_tree(self, minimal_project_dir, capsys):
        result = main(["tree", str(minimal_project_dir)])
        assert result == 0
        output = capsys.readouterr().out
        assert "Stage" in output
        assert "Sprite1" in output


class TestValidateCommand:
    def test_valid_project(self, minimal_project_dir, capsys):
        result = main(["validate", str(minimal_project_dir)])
        assert result == 0
        output = capsys.readouterr().out
        assert "valid" in output.lower()

    def test_validate_json(self, minimal_project_dir, capsys):
        result = main(["validate", str(minimal_project_dir), "--json"])
        assert result == 0
        data = json.loads(capsys.readouterr().out)
        assert isinstance(data, list)


class TestPackUnpackCommands:
    def test_pack(self, minimal_project_dir, tmp_path, capsys):
        output = tmp_path / "packed.sb3"
        result = main(["pack", str(minimal_project_dir), "-o", str(output)])
        assert result == 0
        assert output.exists()

    def test_unpack(self, minimal_sb3, tmp_path, capsys):
        output = tmp_path / "unpacked"
        result = main(["unpack", str(minimal_sb3), "-o", str(output)])
        assert result == 0
        assert (output / "project.json").exists()


class TestModifyCommands:
    def test_rename_sprite(self, minimal_project_dir, capsys):
        result = main(
            ["rename-sprite", str(minimal_project_dir), "Sprite1", "NewSprite"]
        )
        assert result == 0
        output = capsys.readouterr().out
        assert "NewSprite" in output

    def test_rename_variable(self, minimal_project_dir, capsys):
        result = main(
            ["rename-variable", str(minimal_project_dir), "my variable", "new var"]
        )
        assert result == 0

    def test_set_meta(self, minimal_project_dir, capsys):
        result = main(
            ["set-meta", str(minimal_project_dir), "--key", "vm", "--value", "99.0.0"]
        )
        assert result == 0

    def test_delete_sprite(self, minimal_project_dir, capsys):
        result = main(["delete-sprite", str(minimal_project_dir), "Sprite1"])
        assert result == 0
        output = capsys.readouterr().out
        assert "Deleted" in output


class TestErrorHandling:
    def test_nonexistent_project(self, capsys):
        result = main(["info", "/nonexistent/path"])
        assert result == 1

    def test_rename_nonexistent_sprite(self, minimal_project_dir, capsys):
        result = main(
            ["rename-sprite", str(minimal_project_dir), "NoSprite", "New"]
        )
        assert result == 1


class TestInitCommand:
    def test_init_directory(self, tmp_path, capsys):
        output = tmp_path / "myproject"
        result = main(["init", str(output)])
        assert result == 0
        assert (output / "project.json").exists()
        # Should have at least one SVG asset
        svg_files = list(output.glob("*.svg"))
        assert len(svg_files) >= 1
        output_text = capsys.readouterr().out
        assert "Created project" in output_text

    def test_init_sb3(self, tmp_path, capsys):
        output = tmp_path / "out.sb3"
        result = main(["init", str(output)])
        assert result == 0
        assert output.exists()
        # Should be a valid ZIP
        import zipfile
        with zipfile.ZipFile(output) as zf:
            assert "project.json" in zf.namelist()

    def test_init_with_name(self, tmp_path, capsys):
        output = tmp_path / "proj"
        result = main(["init", str(output), "--name", "MyGame"])
        assert result == 0

    def test_init_with_sprites(self, tmp_path, capsys):
        output = tmp_path / "proj"
        result = main(["init", str(output), "--sprite", "Cat", "--sprite", "Dog"])
        assert result == 0
        output_text = capsys.readouterr().out
        assert "Cat" in output_text
        assert "Dog" in output_text
        # Validate: should have 3 targets (Stage + 2 sprites)
        result2 = main(["info", str(output), "--json"])
        info_json = json.loads(capsys.readouterr().out)
        assert info_json["sprite_count"] == 2

    def test_init_with_script(self, tmp_path, capsys):
        # Write a test script
        script = tmp_path / "stage.scr"
        script.write_text("when flag clicked\nsay [Hello!]\n")
        output = tmp_path / "proj"
        result = main(["init", str(output), "--script", "Stage", str(script)])
        assert result == 0
        output_text = capsys.readouterr().out
        assert "Compiled" in output_text
        # Validate
        result2 = main(["validate", str(output)])
        assert result2 == 0

    def test_init_validates_clean(self, tmp_path, capsys):
        output = tmp_path / "proj"
        main(["init", str(output), "--sprite", "Cat"])
        result = main(["validate", str(output)])
        assert result == 0
