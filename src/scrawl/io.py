"""I/O operations: pack/unpack .sb3, auto-detect project type, load projects."""

from __future__ import annotations

import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Optional

from scrawl.errors import CorruptArchiveError, ProjectNotFoundError
from scrawl.model import ScratchProject


def detect_project_type(path: Path) -> str:
    """
    Returns 'sb3_file' if path is a .sb3 ZIP file,
    'directory' if path is a directory containing project.json.
    Raises ProjectNotFoundError otherwise.
    """
    path = Path(path)
    if not path.exists():
        raise ProjectNotFoundError(f"Path does not exist: {path}")
    if path.is_file():
        if not zipfile.is_zipfile(path):
            # Could still be a raw project.json file
            if path.name == "project.json":
                return "directory"  # treat parent as directory
            raise CorruptArchiveError(f"Not a valid ZIP/.sb3 file: {path}")
        return "sb3_file"
    if path.is_dir():
        if not (path / "project.json").exists():
            raise ProjectNotFoundError(
                f"Directory does not contain project.json: {path}"
            )
        return "directory"
    raise ProjectNotFoundError(f"Unsupported path type: {path}")


def load_project(path: Path) -> ScratchProject:
    """
    Auto-detect input type and load project.
    For .sb3 files, reads project.json from the ZIP in memory.
    For directories, reads project.json from disk.
    """
    path = Path(path)
    ptype = detect_project_type(path)

    if ptype == "sb3_file":
        return _load_from_sb3(path)
    else:
        # directory or raw project.json
        if path.is_file() and path.name == "project.json":
            return ScratchProject.from_file(path)
        return ScratchProject.from_file(path / "project.json")


def _load_from_sb3(sb3_path: Path) -> ScratchProject:
    """Load project.json from a .sb3 ZIP without full extraction."""
    try:
        with zipfile.ZipFile(sb3_path, "r") as zf:
            if "project.json" not in zf.namelist():
                raise ProjectNotFoundError(
                    f"project.json not found inside {sb3_path}"
                )
            text = zf.read("project.json").decode("utf-8")
            project = ScratchProject.from_json_string(text)
            # Store the zip namelist for asset existence checks
            project._zip_names = set(zf.namelist())
            project._sb3_path = sb3_path
            return project
    except zipfile.BadZipFile as e:
        raise CorruptArchiveError(f"Corrupt .sb3 file: {sb3_path}: {e}") from e


def unpack_sb3(sb3_path: Path, output_dir: Path) -> Path:
    """Extract .sb3 ZIP archive to output_dir."""
    sb3_path = Path(sb3_path)
    output_dir = Path(output_dir)

    if not sb3_path.exists():
        raise ProjectNotFoundError(f"File not found: {sb3_path}")
    if not zipfile.is_zipfile(sb3_path):
        raise CorruptArchiveError(f"Not a valid ZIP/.sb3 file: {sb3_path}")

    try:
        with zipfile.ZipFile(sb3_path, "r") as zf:
            if "project.json" not in zf.namelist():
                raise ProjectNotFoundError(
                    f"project.json not found inside {sb3_path}"
                )
            output_dir.mkdir(parents=True, exist_ok=True)
            zf.extractall(output_dir)
    except zipfile.BadZipFile as e:
        raise CorruptArchiveError(f"Corrupt .sb3 file: {sb3_path}: {e}") from e

    return output_dir


def pack_sb3(source_dir: Path, output_path: Path) -> Path:
    """Create .sb3 ZIP from directory containing project.json + assets."""
    source_dir = Path(source_dir)
    output_path = Path(output_path)

    if not source_dir.is_dir():
        raise ProjectNotFoundError(f"Not a directory: {source_dir}")
    project_json = source_dir / "project.json"
    if not project_json.exists():
        raise ProjectNotFoundError(
            f"project.json not found in {source_dir}"
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # Add project.json first
        zf.write(project_json, "project.json")
        # Add all other files (assets)
        for f in sorted(source_dir.iterdir()):
            if f.name == "project.json":
                continue
            if f.is_file() and not f.name.startswith("."):
                zf.write(f, f.name)

    return output_path


def load_project_for_modification(
    path: Path,
) -> tuple[ScratchProject, Path, bool]:
    """
    Load a project for in-place modification.

    For directories: returns (project, dir_path, needs_repack=False)
    For .sb3 files: extracts to temp dir, returns (project, temp_dir, needs_repack=True)
    """
    path = Path(path)
    ptype = detect_project_type(path)

    if ptype == "directory":
        if path.is_file() and path.name == "project.json":
            base = path.parent
        else:
            base = path
        project = ScratchProject.from_file(base / "project.json")
        return (project, base, False)
    else:
        temp_dir = Path(tempfile.mkdtemp(prefix="sb3_mod_"))
        unpack_sb3(path, temp_dir)
        project = ScratchProject.from_file(temp_dir / "project.json")
        return (project, temp_dir, True)


def save_project_after_modification(
    project: ScratchProject,
    work_dir: Path,
    original_path: Path,
    needs_repack: bool,
) -> None:
    """
    Save project.json to work_dir, and if needs_repack is True,
    repack the directory into the original .sb3 path.
    """
    project.save(work_dir / "project.json")
    if needs_repack:
        pack_sb3(work_dir, original_path)
        shutil.rmtree(work_dir, ignore_errors=True)
