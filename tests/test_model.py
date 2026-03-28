"""Tests for scrawl.model — ScratchProject class."""

import json
import pytest
from pathlib import Path

from scrawl.model import ScratchProject
from scrawl.errors import InvalidProjectError, ProjectNotFoundError


class TestScratchProjectConstruction:
    def test_from_dict(self, minimal_project_data):
        project = ScratchProject(minimal_project_data)
        assert len(project.targets) == 2
        assert project.stage is not None
        assert project.stage["name"] == "Stage"

    def test_from_json_string(self, minimal_project_data):
        text = json.dumps(minimal_project_data)
        project = ScratchProject.from_json_string(text)
        assert len(project.sprites) == 1
        assert project.sprites[0]["name"] == "Sprite1"

    def test_from_file(self, minimal_project_dir):
        project = ScratchProject.from_file(minimal_project_dir / "project.json")
        assert project.base_path == minimal_project_dir
        assert len(project.targets) == 2

    def test_invalid_json_raises(self):
        with pytest.raises(InvalidProjectError, match="Invalid JSON"):
            ScratchProject.from_json_string("{bad json")

    def test_non_object_raises(self):
        with pytest.raises(InvalidProjectError, match="root must be"):
            ScratchProject.from_json_string("[1, 2, 3]")

    def test_missing_file_raises(self):
        with pytest.raises(ProjectNotFoundError):
            ScratchProject.from_file(Path("/nonexistent/project.json"))


class TestAccessors:
    def test_stage(self, minimal_project_data):
        project = ScratchProject(minimal_project_data)
        assert project.stage["isStage"] is True

    def test_sprites(self, minimal_project_data):
        project = ScratchProject(minimal_project_data)
        assert len(project.sprites) == 1
        assert project.sprites[0]["name"] == "Sprite1"

    def test_get_target_by_name(self, minimal_project_data):
        project = ScratchProject(minimal_project_data)
        t = project.get_target_by_name("Sprite1")
        assert t is not None
        assert t["name"] == "Sprite1"
        assert project.get_target_by_name("Nonexistent") is None

    def test_extensions(self, minimal_project_data):
        project = ScratchProject(minimal_project_data)
        assert project.extensions == []

    def test_meta(self, minimal_project_data):
        project = ScratchProject(minimal_project_data)
        assert project.meta["semver"] == "3.0.0"

    def test_monitors(self, minimal_project_data):
        project = ScratchProject(minimal_project_data)
        assert len(project.monitors) == 1


class TestIterators:
    def test_all_variables(self, minimal_project_data):
        project = ScratchProject(minimal_project_data)
        vars_list = list(project.all_variables())
        assert len(vars_list) == 2
        names = {v[2] for v in vars_list}
        assert "my variable" in names
        assert "sprite var" in names

    def test_all_lists(self, minimal_project_data):
        project = ScratchProject(minimal_project_data)
        lists = list(project.all_lists())
        assert len(lists) == 1
        assert lists[0][2] == "my list"

    def test_all_blocks(self, minimal_project_data):
        project = ScratchProject(minimal_project_data)
        blocks = list(project.all_blocks())
        assert len(blocks) == 3  # 2 in stage, 1 in sprite

    def test_all_assets_referenced(self, minimal_project_data):
        project = ScratchProject(minimal_project_data)
        assets = list(project.all_assets_referenced())
        # 1 costume + 1 sound in stage, 1 costume in sprite
        assert len(assets) == 3


class TestRoundTrip:
    def test_json_roundtrip(self, minimal_project_data):
        project = ScratchProject(minimal_project_data)
        text = project.to_json_string()
        project2 = ScratchProject.from_json_string(text)
        assert project.raw == project2.raw

    def test_save_and_reload(self, minimal_project_dir):
        project = ScratchProject.from_file(minimal_project_dir / "project.json")
        project.save()
        project2 = ScratchProject.from_file(minimal_project_dir / "project.json")
        assert project.raw == project2.raw
