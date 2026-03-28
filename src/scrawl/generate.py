"""Project generator — create new Scratch 3.0 projects from scratch.

Provides functions to create a minimal valid project structure,
add sprites, and write project files to disk.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from scrawl.errors import ScrawlError

# ---------------------------------------------------------------------------
# Default asset SVGs
# ---------------------------------------------------------------------------

# 480x360 blank white backdrop for the Stage
BLANK_STAGE_SVG = '<svg xmlns="http://www.w3.org/2000/svg" width="480" height="360"></svg>'

# Small blue circle sprite (matches Scratch's default blue #4C97FF)
BLANK_SPRITE_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="96" height="100">'
    '<circle cx="48" cy="50" r="40" fill="#4C97FF"/>'
    '</svg>'
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _compute_asset_id(content: bytes) -> str:
    """Compute the MD5 hex digest of content (Scratch's asset ID convention)."""
    return hashlib.md5(content).hexdigest()


def _make_costume(
    name: str,
    svg_content: str,
    rotation_center_x: int,
    rotation_center_y: int,
) -> tuple[dict[str, Any], str, bytes]:
    """Build a costume entry.

    Returns:
        (costume_dict, md5ext_filename, file_bytes)
    """
    file_bytes = svg_content.encode("utf-8")
    asset_id = _compute_asset_id(file_bytes)
    md5ext = f"{asset_id}.svg"

    costume: dict[str, Any] = {
        "name": name,
        "dataFormat": "svg",
        "assetId": asset_id,
        "md5ext": md5ext,
        "rotationCenterX": rotation_center_x,
        "rotationCenterY": rotation_center_y,
    }
    return costume, md5ext, file_bytes


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def create_project(name: str = "Project") -> tuple[dict[str, Any], dict[str, bytes]]:
    """Create a minimal valid Scratch 3.0 project.

    Args:
        name: Project name (stored in meta.agent field context).

    Returns:
        (project_data, asset_files) where asset_files is {filename: bytes}.
    """
    asset_files: dict[str, bytes] = {}

    backdrop, md5ext, file_bytes = _make_costume(
        "backdrop1", BLANK_STAGE_SVG, 240, 180
    )
    asset_files[md5ext] = file_bytes

    stage: dict[str, Any] = {
        "isStage": True,
        "name": "Stage",
        "variables": {},
        "lists": {},
        "broadcasts": {},
        "blocks": {},
        "comments": {},
        "currentCostume": 0,
        "costumes": [backdrop],
        "sounds": [],
        "volume": 100,
        "layerOrder": 0,
        "tempo": 60,
        "videoTransparency": 50,
        "videoState": "off",
        "textToSpeechLanguage": None,
    }

    project_data: dict[str, Any] = {
        "targets": [stage],
        "monitors": [],
        "extensions": [],
        "meta": {
            "semver": "3.0.0",
            "vm": "0.2.0",
            "agent": "scrawl",
        },
    }

    return project_data, asset_files


def add_sprite(
    project_data: dict[str, Any],
    name: str,
    x: int = 0,
    y: int = 0,
) -> dict[str, bytes]:
    """Add a sprite target to the project.

    Args:
        project_data: The project dict (mutated in place).
        name: Sprite name.
        x: Initial x position.
        y: Initial y position.

    Returns:
        Asset files dict for the new sprite.

    Raises:
        ScrawlError: If a target with that name already exists.
    """
    existing_names = {t["name"] for t in project_data["targets"]}
    if name in existing_names:
        raise ScrawlError(f"Target '{name}' already exists")

    asset_files: dict[str, bytes] = {}

    costume, md5ext, file_bytes = _make_costume(
        "costume1", BLANK_SPRITE_SVG, 48, 50
    )
    asset_files[md5ext] = file_bytes

    layer_order = len(project_data["targets"])

    sprite: dict[str, Any] = {
        "isStage": False,
        "name": name,
        "variables": {},
        "lists": {},
        "broadcasts": {},
        "blocks": {},
        "comments": {},
        "currentCostume": 0,
        "costumes": [costume],
        "sounds": [],
        "volume": 100,
        "layerOrder": layer_order,
        "visible": True,
        "x": x,
        "y": y,
        "size": 100,
        "direction": 90,
        "draggable": False,
        "rotationStyle": "all around",
    }

    project_data["targets"].append(sprite)
    return asset_files


def write_project(
    project_data: dict[str, Any],
    asset_files: dict[str, bytes],
    output_dir: Path,
) -> Path:
    """Write project.json and asset files to a directory.

    Creates the directory if it doesn't exist.

    Returns:
        The output directory path.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    project_json = output_dir / "project.json"
    project_json.write_text(
        json.dumps(project_data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    for filename, content in asset_files.items():
        (output_dir / filename).write_bytes(content)

    return output_dir
