"""Tests for scrawl.validate — validation rules."""

import copy
import pytest

from scrawl.model import ScratchProject
from scrawl.validate import validate_project


class TestValidProject:
    def test_minimal_project_is_valid(self, minimal_project_data):
        project = ScratchProject(minimal_project_data)
        issues = validate_project(project)
        errors = [i for i in issues if i.severity == "error"]
        assert len(errors) == 0

    def test_real_project_is_valid(self, real_project_path):
        project = ScratchProject.from_file(real_project_path / "project.json")
        issues = validate_project(project)
        errors = [i for i in issues if i.severity == "error"]
        assert len(errors) == 0


class TestStructureChecks:
    def test_missing_targets(self):
        project = ScratchProject({"meta": {}})
        issues = validate_project(project)
        msgs = [i.message for i in issues if i.severity == "error"]
        assert any("targets" in m for m in msgs)

    def test_empty_targets(self):
        project = ScratchProject({"targets": [], "meta": {}})
        issues = validate_project(project)
        msgs = [i.message for i in issues if i.severity == "error"]
        assert any("non-empty" in m for m in msgs)

    def test_missing_meta_is_warning(self):
        project = ScratchProject({"targets": [{"isStage": True, "name": "Stage", "costumes": [{"md5ext": "a.svg"}], "blocks": {}}]})
        issues = validate_project(project)
        warnings = [i for i in issues if i.severity == "warning"]
        assert any("meta" in w.message for w in warnings)


class TestStageIsFirst:
    def test_stage_not_first(self, minimal_project_data):
        data = copy.deepcopy(minimal_project_data)
        data["targets"].reverse()  # Put sprite first
        project = ScratchProject(data)
        issues = validate_project(project)
        assert any("isStage" in i.message for i in issues if i.severity == "error")


class TestCostumesExist:
    def test_no_costumes(self, minimal_project_data):
        data = copy.deepcopy(minimal_project_data)
        data["targets"][0]["costumes"] = []
        project = ScratchProject(data)
        issues = validate_project(project)
        assert any("no costumes" in i.message for i in issues if i.severity == "error")


class TestAssetChecks:
    def test_missing_asset_file(self, minimal_project_dir):
        import os
        # Delete one asset file
        (minimal_project_dir / "bcf454acf82e4504149f7ffe07081dbc.svg").unlink()
        project = ScratchProject.from_file(minimal_project_dir / "project.json")
        issues = validate_project(project)
        assert any(
            "bcf454acf82e4504149f7ffe07081dbc.svg" in i.message
            for i in issues
            if i.severity == "error"
        )


class TestBlockReferences:
    def test_invalid_next_reference(self, minimal_project_data):
        data = copy.deepcopy(minimal_project_data)
        data["targets"][0]["blocks"]["block1"]["next"] = "nonexistent"
        project = ScratchProject(data)
        issues = validate_project(project)
        assert any(
            "nonexistent" in i.message
            for i in issues
            if i.category == "block" and i.severity == "error"
        )

    def test_invalid_parent_reference(self, minimal_project_data):
        data = copy.deepcopy(minimal_project_data)
        data["targets"][0]["blocks"]["block2"]["parent"] = "nonexistent"
        project = ScratchProject(data)
        issues = validate_project(project)
        assert any(
            "parent" in i.message
            for i in issues
            if i.category == "block" and i.severity == "error"
        )


class TestVariableReferences:
    def test_invalid_variable_field(self, minimal_project_data):
        data = copy.deepcopy(minimal_project_data)
        data["targets"][0]["blocks"]["block2"]["fields"]["VARIABLE"] = [
            "missing var",
            "nonexistent_id",
        ]
        project = ScratchProject(data)
        issues = validate_project(project)
        assert any(
            "nonexistent_id" in i.message
            for i in issues
            if i.category == "variable"
        )


class TestExtensionDeclarations:
    def test_undeclared_extension(self, minimal_project_data):
        data = copy.deepcopy(minimal_project_data)
        data["targets"][0]["blocks"]["pen_block"] = {
            "opcode": "pen_clear",
            "next": None,
            "parent": None,
            "inputs": {},
            "fields": {},
            "shadow": False,
            "topLevel": True,
        }
        data["extensions"] = []  # pen not declared
        project = ScratchProject(data)
        issues = validate_project(project)
        assert any(
            "pen" in i.message and "not declared" in i.message
            for i in issues
            if i.severity == "warning"
        )


class TestCostumeIndices:
    def test_out_of_range_index(self, minimal_project_data):
        data = copy.deepcopy(minimal_project_data)
        data["targets"][0]["currentCostume"] = 99
        project = ScratchProject(data)
        issues = validate_project(project)
        assert any(
            "currentCostume" in i.message
            for i in issues
            if i.severity == "error"
        )


class TestMetaSemver:
    def test_valid_semver_no_issues(self, minimal_project_data):
        data = copy.deepcopy(minimal_project_data)
        data["meta"] = {"semver": "3.0.0"}
        project = ScratchProject(data)
        issues = validate_project(project)
        assert not any("semver" in i.message for i in issues)

    def test_invalid_semver(self, minimal_project_data):
        data = copy.deepcopy(minimal_project_data)
        data["meta"] = {"semver": "2.0.0"}
        project = ScratchProject(data)
        issues = validate_project(project)
        assert any("semver" in i.message for i in issues if i.severity == "warning")


class TestStageConstraints:
    def test_stage_wrong_name(self, minimal_project_data):
        data = copy.deepcopy(minimal_project_data)
        data["targets"][0]["name"] = "NotStage"
        project = ScratchProject(data)
        issues = validate_project(project)
        assert any("Stage" in i.message for i in issues if i.severity == "warning")

    def test_stage_wrong_layer_order(self, minimal_project_data):
        data = copy.deepcopy(minimal_project_data)
        data["targets"][0]["layerOrder"] = 5
        project = ScratchProject(data)
        issues = validate_project(project)
        assert any("layerOrder" in i.message for i in issues if i.severity == "warning")

    def test_stage_invalid_video_state(self, minimal_project_data):
        data = copy.deepcopy(minimal_project_data)
        data["targets"][0]["videoState"] = "invalid"
        project = ScratchProject(data)
        issues = validate_project(project)
        assert any("videoState" in i.message for i in issues if i.severity == "warning")


class TestSpriteConstraints:
    def test_reserved_sprite_name(self, minimal_project_data):
        data = copy.deepcopy(minimal_project_data)
        data["targets"][1]["name"] = "_stage_"
        project = ScratchProject(data)
        issues = validate_project(project)
        assert any("reserved" in i.message for i in issues if i.severity == "error")

    def test_sprite_invalid_rotation_style(self, minimal_project_data):
        data = copy.deepcopy(minimal_project_data)
        data["targets"][1]["rotationStyle"] = "spin"
        project = ScratchProject(data)
        issues = validate_project(project)
        assert any("rotationStyle" in i.message for i in issues if i.severity == "warning")

    def test_sprite_zero_layer_order(self, minimal_project_data):
        data = copy.deepcopy(minimal_project_data)
        data["targets"][1]["layerOrder"] = 0
        project = ScratchProject(data)
        issues = validate_project(project)
        assert any("layerOrder" in i.message for i in issues if i.severity == "warning")


class TestAssetFormats:
    def test_invalid_costume_asset_id(self, minimal_project_data):
        data = copy.deepcopy(minimal_project_data)
        data["targets"][0]["costumes"][0]["assetId"] = "not-a-valid-hex"
        project = ScratchProject(data)
        issues = validate_project(project)
        assert any("assetId" in i.message for i in issues if i.severity == "error")

    def test_invalid_costume_format(self, minimal_project_data):
        data = copy.deepcopy(minimal_project_data)
        data["targets"][0]["costumes"][0]["dataFormat"] = "tiff"
        project = ScratchProject(data)
        issues = validate_project(project)
        assert any("dataFormat" in i.message for i in issues if i.severity == "error")

    def test_valid_formats_pass(self, minimal_project_data):
        project = ScratchProject(minimal_project_data)
        issues = validate_project(project)
        assert not any(
            "dataFormat" in i.message for i in issues if i.severity == "error"
        )


class TestBlockOpcodes:
    def test_block_missing_opcode(self, minimal_project_data):
        data = copy.deepcopy(minimal_project_data)
        data["targets"][0]["blocks"]["bad_block"] = {
            "next": None,
            "parent": None,
            "inputs": {},
            "fields": {},
            "shadow": False,
            "topLevel": True,
        }
        project = ScratchProject(data)
        issues = validate_project(project)
        assert any("opcode" in i.message for i in issues if i.severity == "error")


class TestComments:
    def test_long_comment_warning(self, minimal_project_data):
        data = copy.deepcopy(minimal_project_data)
        data["targets"][0]["comments"] = {
            "c1": {"text": "x" * 9000, "x": 0, "y": 0, "width": 200, "height": 200}
        }
        project = ScratchProject(data)
        issues = validate_project(project)
        assert any("8000" in i.message for i in issues if i.severity == "warning")
