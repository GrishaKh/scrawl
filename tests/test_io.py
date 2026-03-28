"""Tests for scrawl.io — pack/unpack and project loading."""

import json
import zipfile
import pytest
from pathlib import Path

from scrawl.io import (
    detect_project_type,
    load_project,
    unpack_sb3,
    pack_sb3,
    load_project_for_modification,
    save_project_after_modification,
)
from scrawl.errors import ProjectNotFoundError, CorruptArchiveError


class TestDetectProjectType:
    def test_directory(self, minimal_project_dir):
        assert detect_project_type(minimal_project_dir) == "directory"

    def test_sb3_file(self, minimal_sb3):
        assert detect_project_type(minimal_sb3) == "sb3_file"

    def test_nonexistent_raises(self):
        with pytest.raises(ProjectNotFoundError):
            detect_project_type(Path("/nonexistent"))

    def test_dir_without_project_json_raises(self, tmp_path):
        with pytest.raises(ProjectNotFoundError, match="project.json"):
            detect_project_type(tmp_path)

    def test_non_zip_file_raises(self, tmp_path):
        f = tmp_path / "bad.sb3"
        f.write_text("not a zip")
        with pytest.raises(CorruptArchiveError):
            detect_project_type(f)


class TestLoadProject:
    def test_load_from_directory(self, minimal_project_dir):
        project = load_project(minimal_project_dir)
        assert len(project.targets) == 2
        assert project.base_path == minimal_project_dir

    def test_load_from_sb3(self, minimal_sb3):
        project = load_project(minimal_sb3)
        assert len(project.targets) == 2
        assert hasattr(project, "_zip_names")


class TestUnpackSb3:
    def test_unpack(self, minimal_sb3, tmp_path):
        output = tmp_path / "unpacked"
        unpack_sb3(minimal_sb3, output)
        assert (output / "project.json").exists()
        data = json.loads((output / "project.json").read_text())
        assert len(data["targets"]) == 2

    def test_unpack_nonexistent_raises(self, tmp_path):
        with pytest.raises(ProjectNotFoundError):
            unpack_sb3(tmp_path / "missing.sb3", tmp_path / "out")


class TestPackSb3:
    def test_pack(self, minimal_project_dir, tmp_path):
        output = tmp_path / "output.sb3"
        pack_sb3(minimal_project_dir, output)
        assert output.exists()
        assert zipfile.is_zipfile(output)
        with zipfile.ZipFile(output, "r") as zf:
            assert "project.json" in zf.namelist()

    def test_pack_missing_project_json_raises(self, tmp_path):
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        with pytest.raises(ProjectNotFoundError):
            pack_sb3(empty_dir, tmp_path / "out.sb3")


class TestRoundTrip:
    def test_pack_unpack_roundtrip(self, minimal_project_dir, tmp_path):
        sb3_path = tmp_path / "test.sb3"
        pack_sb3(minimal_project_dir, sb3_path)

        unpacked = tmp_path / "unpacked"
        unpack_sb3(sb3_path, unpacked)

        original = json.loads((minimal_project_dir / "project.json").read_text())
        result = json.loads((unpacked / "project.json").read_text())
        assert original == result


class TestModificationFlow:
    def test_modify_directory(self, minimal_project_dir):
        project, work_dir, needs_repack = load_project_for_modification(
            minimal_project_dir
        )
        assert needs_repack is False
        assert work_dir == minimal_project_dir
        project.raw["meta"]["vm"] = "99.0.0"
        save_project_after_modification(
            project, work_dir, minimal_project_dir, needs_repack
        )
        reloaded = load_project(minimal_project_dir)
        assert reloaded.meta["vm"] == "99.0.0"

    def test_modify_sb3(self, minimal_sb3, tmp_path):
        project, work_dir, needs_repack = load_project_for_modification(minimal_sb3)
        assert needs_repack is True
        project.raw["meta"]["vm"] = "99.0.0"
        save_project_after_modification(
            project, work_dir, minimal_sb3, needs_repack
        )
        reloaded = load_project(minimal_sb3)
        assert reloaded.meta["vm"] == "99.0.0"
