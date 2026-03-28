"""Tests for scrawl.modify — mutation operations."""

import copy
import pytest

from scrawl.model import ScratchProject
from scrawl.modify import rename_sprite, rename_variable, delete_sprite, set_meta
from scrawl.errors import ScrawlError, SpriteNotFoundError, VariableNotFoundError


class TestRenameSprite:
    def test_basic_rename(self, minimal_project_data):
        project = ScratchProject(minimal_project_data)
        rename_sprite(project, "Sprite1", "MySprite")
        assert project.get_target_by_name("MySprite") is not None
        assert project.get_target_by_name("Sprite1") is None

    def test_not_found_raises(self, minimal_project_data):
        project = ScratchProject(minimal_project_data)
        with pytest.raises(SpriteNotFoundError):
            rename_sprite(project, "Nonexistent", "New")

    def test_cannot_rename_stage(self, minimal_project_data):
        project = ScratchProject(minimal_project_data)
        with pytest.raises(ScrawlError, match="stage"):
            rename_sprite(project, "Stage", "NewStage")

    def test_duplicate_name_raises(self, minimal_project_data):
        project = ScratchProject(minimal_project_data)
        with pytest.raises(ScrawlError, match="already exists"):
            rename_sprite(project, "Sprite1", "Stage")

    def test_updates_monitors(self, minimal_project_data):
        data = copy.deepcopy(minimal_project_data)
        data["monitors"].append(
            {
                "id": "test",
                "spriteName": "Sprite1",
                "params": {"VARIABLE": "sprite var"},
            }
        )
        project = ScratchProject(data)
        rename_sprite(project, "Sprite1", "RenamedSprite")
        assert project.monitors[1]["spriteName"] == "RenamedSprite"


class TestRenameVariable:
    def test_rename_global_variable(self, minimal_project_data):
        project = ScratchProject(minimal_project_data)
        rename_variable(project, "my variable", "renamed var")
        # Check the variable entry was updated
        stage = project.stage
        assert stage["variables"]["var1"][0] == "renamed var"

    def test_rename_updates_block_fields(self, minimal_project_data):
        project = ScratchProject(minimal_project_data)
        rename_variable(project, "my variable", "renamed var")
        block = project.stage["blocks"]["block2"]
        assert block["fields"]["VARIABLE"][0] == "renamed var"

    def test_rename_updates_monitors(self, minimal_project_data):
        project = ScratchProject(minimal_project_data)
        rename_variable(project, "my variable", "renamed var")
        assert project.monitors[0]["params"]["VARIABLE"] == "renamed var"

    def test_rename_sprite_variable(self, minimal_project_data):
        project = ScratchProject(minimal_project_data)
        rename_variable(project, "sprite var", "new sprite var", sprite_name="Sprite1")
        sprite = project.get_target_by_name("Sprite1")
        assert sprite["variables"]["sprvar1"][0] == "new sprite var"

    def test_not_found_raises(self, minimal_project_data):
        project = ScratchProject(minimal_project_data)
        with pytest.raises(VariableNotFoundError):
            rename_variable(project, "nonexistent", "new")

    def test_sprite_not_found_raises(self, minimal_project_data):
        project = ScratchProject(minimal_project_data)
        with pytest.raises(SpriteNotFoundError):
            rename_variable(project, "my variable", "new", sprite_name="Nonexistent")

    def test_rename_list(self, minimal_project_data):
        project = ScratchProject(minimal_project_data)
        rename_variable(project, "my list", "renamed list")
        stage = project.stage
        assert stage["lists"]["list1"][0] == "renamed list"


class TestDeleteSprite:
    def test_basic_delete(self, minimal_project_data):
        project = ScratchProject(minimal_project_data)
        deleted = delete_sprite(project, "Sprite1")
        assert project.get_target_by_name("Sprite1") is None
        assert len(project.sprites) == 0

    def test_not_found_raises(self, minimal_project_data):
        project = ScratchProject(minimal_project_data)
        with pytest.raises(SpriteNotFoundError):
            delete_sprite(project, "Nonexistent")

    def test_cannot_delete_stage(self, minimal_project_data):
        project = ScratchProject(minimal_project_data)
        with pytest.raises(ScrawlError, match="stage"):
            delete_sprite(project, "Stage")

    def test_removes_sprite_monitors(self, minimal_project_data):
        data = copy.deepcopy(minimal_project_data)
        data["monitors"].append(
            {
                "id": "sprite_mon",
                "spriteName": "Sprite1",
                "params": {"VARIABLE": "sprite var"},
            }
        )
        project = ScratchProject(data)
        delete_sprite(project, "Sprite1")
        assert all(m.get("spriteName") != "Sprite1" for m in project.monitors)

    def test_exclusive_assets_deleted(self, minimal_project_dir):
        project = ScratchProject.from_file(minimal_project_dir / "project.json")
        deleted = delete_sprite(project, "Sprite1")
        assert "bcf454acf82e4504149f7ffe07081dbc.svg" in deleted
        assert not (minimal_project_dir / "bcf454acf82e4504149f7ffe07081dbc.svg").exists()


class TestSetMeta:
    def test_set_known_key(self, minimal_project_data):
        project = ScratchProject(minimal_project_data)
        set_meta(project, "vm", "99.0.0")
        assert project.meta["vm"] == "99.0.0"

    def test_unknown_key_raises(self, minimal_project_data):
        project = ScratchProject(minimal_project_data)
        with pytest.raises(ScrawlError, match="Unknown meta key"):
            set_meta(project, "unknown", "value")
