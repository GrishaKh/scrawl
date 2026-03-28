"""Tests for the project generator."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scrawl.errors import ScrawlError
from scrawl.generate import (
    BLANK_SPRITE_SVG,
    BLANK_STAGE_SVG,
    add_sprite,
    create_project,
    write_project,
)
from scrawl.model import ScratchProject
from scrawl.validate import validate_project


# ---------------------------------------------------------------------------
# create_project
# ---------------------------------------------------------------------------


class TestCreateProject:
    def test_returns_valid_structure(self):
        data, assets = create_project()
        assert "targets" in data
        assert "meta" in data
        assert "extensions" in data
        assert len(data["targets"]) == 1
        assert data["targets"][0]["isStage"] is True
        assert data["targets"][0]["name"] == "Stage"

    def test_stage_has_costume(self):
        data, assets = create_project()
        stage = data["targets"][0]
        assert len(stage["costumes"]) == 1
        costume = stage["costumes"][0]
        assert costume["name"] == "backdrop1"
        assert costume["dataFormat"] == "svg"
        assert "assetId" in costume
        assert "md5ext" in costume

    def test_asset_files_match_costumes(self):
        data, assets = create_project()
        stage = data["targets"][0]
        md5ext = stage["costumes"][0]["md5ext"]
        assert md5ext in assets
        assert len(assets) == 1

    def test_passes_validation(self, tmp_path):
        data, assets = create_project()
        write_project(data, assets, tmp_path)
        project = ScratchProject(data, base_path=tmp_path)
        issues = validate_project(project)
        errors = [i for i in issues if i.severity == "error"]
        assert len(errors) == 0

    def test_custom_name(self):
        data, assets = create_project(name="MyGame")
        assert data["meta"]["agent"] == "scrawl"
        # Project is still valid
        assert len(data["targets"]) == 1

    def test_meta_fields(self):
        data, _ = create_project()
        assert data["meta"]["semver"] == "3.0.0"
        assert data["meta"]["vm"] == "0.2.0"

    def test_stage_has_empty_blocks(self):
        data, _ = create_project()
        stage = data["targets"][0]
        assert stage["blocks"] == {}
        assert stage["variables"] == {}
        assert stage["lists"] == {}
        assert stage["broadcasts"] == {}


# ---------------------------------------------------------------------------
# add_sprite
# ---------------------------------------------------------------------------


class TestAddSprite:
    def test_adds_sprite_target(self):
        data, _ = create_project()
        add_sprite(data, "Cat")
        assert len(data["targets"]) == 2
        sprite = data["targets"][1]
        assert sprite["name"] == "Cat"
        assert sprite["isStage"] is False

    def test_sprite_has_costume(self):
        data, _ = create_project()
        add_sprite(data, "Cat")
        sprite = data["targets"][1]
        assert len(sprite["costumes"]) == 1
        assert sprite["costumes"][0]["name"] == "costume1"

    def test_sprite_assets_returned(self):
        data, _ = create_project()
        sprite_assets = add_sprite(data, "Cat")
        assert len(sprite_assets) == 1
        filename = list(sprite_assets.keys())[0]
        assert filename.endswith(".svg")

    def test_duplicate_name_raises(self):
        data, _ = create_project()
        with pytest.raises(ScrawlError, match="already exists"):
            add_sprite(data, "Stage")

    def test_duplicate_sprite_name_raises(self):
        data, _ = create_project()
        add_sprite(data, "Cat")
        with pytest.raises(ScrawlError, match="already exists"):
            add_sprite(data, "Cat")

    def test_layer_order(self):
        data, _ = create_project()
        add_sprite(data, "Cat")
        add_sprite(data, "Dog")
        assert data["targets"][1]["layerOrder"] == 1
        assert data["targets"][2]["layerOrder"] == 2

    def test_sprite_position(self):
        data, _ = create_project()
        add_sprite(data, "Cat", x=100, y=-50)
        sprite = data["targets"][1]
        assert sprite["x"] == 100
        assert sprite["y"] == -50

    def test_passes_validation_with_sprites(self, tmp_path):
        data, assets = create_project()
        assets.update(add_sprite(data, "Cat"))
        assets.update(add_sprite(data, "Dog"))
        write_project(data, assets, tmp_path)
        project = ScratchProject(data, base_path=tmp_path)
        issues = validate_project(project)
        errors = [i for i in issues if i.severity == "error"]
        assert len(errors) == 0


# ---------------------------------------------------------------------------
# write_project
# ---------------------------------------------------------------------------


class TestWriteProject:
    def test_writes_project_json(self, tmp_path):
        data, assets = create_project()
        write_project(data, assets, tmp_path)
        project_json = tmp_path / "project.json"
        assert project_json.exists()
        loaded = json.loads(project_json.read_text())
        assert "targets" in loaded

    def test_writes_asset_files(self, tmp_path):
        data, assets = create_project()
        write_project(data, assets, tmp_path)
        for filename in assets:
            assert (tmp_path / filename).exists()

    def test_creates_directory(self, tmp_path):
        nested = tmp_path / "sub" / "dir"
        data, assets = create_project()
        write_project(data, assets, nested)
        assert nested.exists()
        assert (nested / "project.json").exists()

    def test_asset_content_matches(self, tmp_path):
        data, assets = create_project()
        write_project(data, assets, tmp_path)
        for filename, content in assets.items():
            assert (tmp_path / filename).read_bytes() == content
