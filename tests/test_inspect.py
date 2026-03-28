"""Tests for scrawl.inspect — query functions."""

from scrawl.model import ScratchProject
from scrawl.inspect import (
    get_project_info,
    get_sprites,
    get_variables,
    get_block_stats,
    get_assets,
    get_project_tree,
)


class TestGetProjectInfo:
    def test_counts(self, minimal_project_data):
        project = ScratchProject(minimal_project_data)
        info = get_project_info(project)
        assert info["sprite_count"] == 1
        assert info["variable_count"] == 2  # 1 global + 1 sprite
        assert info["list_count"] == 1
        assert info["block_count"] == 3
        assert info["costume_count"] == 2  # 1 stage + 1 sprite
        assert info["sound_count"] == 1
        assert info["monitor_count"] == 1
        assert info["extensions"] == []
        assert info["meta"]["semver"] == "3.0.0"


class TestGetSprites:
    def test_all_targets_listed(self, minimal_project_data):
        project = ScratchProject(minimal_project_data)
        sprites = get_sprites(project)
        assert len(sprites) == 2
        assert sprites[0]["name"] == "Stage"
        assert sprites[0]["is_stage"] is True
        assert sprites[1]["name"] == "Sprite1"
        assert sprites[1]["is_stage"] is False

    def test_sprite_details(self, minimal_project_data):
        project = ScratchProject(minimal_project_data)
        sprites = get_sprites(project)
        sprite = sprites[1]
        assert sprite["x"] == 0
        assert sprite["y"] == 0
        assert sprite["size"] == 100
        assert sprite["visible"] is True
        assert sprite["costume_count"] == 1
        assert sprite["block_count"] == 1


class TestGetVariables:
    def test_variables_and_lists(self, minimal_project_data):
        project = ScratchProject(minimal_project_data)
        variables = get_variables(project)
        names = {v["name"] for v in variables}
        assert "my variable" in names
        assert "sprite var" in names
        assert "my list" in names

    def test_scopes(self, minimal_project_data):
        project = ScratchProject(minimal_project_data)
        variables = get_variables(project)
        by_name = {v["name"]: v for v in variables}
        assert by_name["my variable"]["scope"] == "global"
        assert by_name["sprite var"]["scope"] == "Sprite1"
        assert by_name["my list"]["scope"] == "global"
        assert by_name["my list"]["type"] == "list"


class TestGetBlockStats:
    def test_totals(self, minimal_project_data):
        project = ScratchProject(minimal_project_data)
        stats = get_block_stats(project)
        assert stats["total_blocks"] == 3
        assert stats["top_level_stacks"] == 2  # 1 in stage, 1 in sprite
        assert "event" in stats["by_category"]
        assert "data" in stats["by_category"]


class TestGetAssets:
    def test_asset_list(self, minimal_project_dir):
        project = ScratchProject.from_file(minimal_project_dir / "project.json")
        assets = get_assets(project)
        assert len(assets) == 3  # 2 costumes + 1 sound
        for a in assets:
            assert a["file_exists"] is True


class TestGetProjectTree:
    def test_tree_structure(self, minimal_project_data):
        project = ScratchProject(minimal_project_data)
        tree = get_project_tree(project)
        assert tree["name"] == "Stage"
        assert len(tree["targets"]) == 2
        stage_tree = tree["targets"][0]
        assert stage_tree["is_stage"] is True
        assert len(stage_tree["costumes"]) == 1
        assert stage_tree["block_count"] == 2


class TestRealProject:
    def test_info_on_real_project(self, real_project_path):
        project = ScratchProject.from_file(real_project_path / "project.json")
        info = get_project_info(project)
        assert info["sprite_count"] == 37
        assert info["block_count"] > 1000
        assert "pen" in info["extensions"]
