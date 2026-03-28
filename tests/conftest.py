"""Shared test fixtures for scrawl tests."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest


def _minimal_project_data() -> dict:
    """Return a minimal valid Scratch 3.0 project dict."""
    return {
        "targets": [
            {
                "isStage": True,
                "name": "Stage",
                "variables": {
                    "var1": ["my variable", 0],
                },
                "lists": {
                    "list1": ["my list", [1, 2, 3]],
                },
                "broadcasts": {},
                "blocks": {
                    "block1": {
                        "opcode": "event_whenflagclicked",
                        "next": "block2",
                        "parent": None,
                        "inputs": {},
                        "fields": {},
                        "shadow": False,
                        "topLevel": True,
                        "x": 0,
                        "y": 0,
                    },
                    "block2": {
                        "opcode": "data_setvariableto",
                        "next": None,
                        "parent": "block1",
                        "inputs": {
                            "VALUE": [1, [10, "hello"]],
                        },
                        "fields": {
                            "VARIABLE": ["my variable", "var1"],
                        },
                        "shadow": False,
                        "topLevel": False,
                    },
                },
                "comments": {},
                "currentCostume": 0,
                "costumes": [
                    {
                        "name": "backdrop1",
                        "dataFormat": "svg",
                        "assetId": "cd21514d0531fdffb22204e0ec5ed84a",
                        "md5ext": "cd21514d0531fdffb22204e0ec5ed84a.svg",
                        "rotationCenterX": 240,
                        "rotationCenterY": 180,
                    }
                ],
                "sounds": [
                    {
                        "name": "pop",
                        "assetId": "83a9787d4cb6f3b7632b4ddfebf74367",
                        "dataFormat": "wav",
                        "format": "",
                        "rate": 48000,
                        "sampleCount": 1032,
                        "md5ext": "83a9787d4cb6f3b7632b4ddfebf74367.wav",
                    }
                ],
                "volume": 100,
                "layerOrder": 0,
                "tempo": 60,
                "videoTransparency": 50,
                "videoState": "off",
                "textToSpeechLanguage": None,
            },
            {
                "isStage": False,
                "name": "Sprite1",
                "variables": {
                    "sprvar1": ["sprite var", 10],
                },
                "lists": {},
                "broadcasts": {},
                "blocks": {
                    "sblock1": {
                        "opcode": "event_whenflagclicked",
                        "next": None,
                        "parent": None,
                        "inputs": {},
                        "fields": {},
                        "shadow": False,
                        "topLevel": True,
                        "x": 0,
                        "y": 0,
                    },
                },
                "comments": {},
                "currentCostume": 0,
                "costumes": [
                    {
                        "name": "costume1",
                        "dataFormat": "svg",
                        "assetId": "bcf454acf82e4504149f7ffe07081dbc",
                        "md5ext": "bcf454acf82e4504149f7ffe07081dbc.svg",
                        "rotationCenterX": 48,
                        "rotationCenterY": 50,
                    }
                ],
                "sounds": [],
                "volume": 100,
                "layerOrder": 1,
                "visible": True,
                "x": 0,
                "y": 0,
                "size": 100,
                "direction": 90,
                "draggable": False,
                "rotationStyle": "all around",
            },
        ],
        "monitors": [
            {
                "id": "var1",
                "mode": "default",
                "opcode": "data_variable",
                "params": {"VARIABLE": "my variable"},
                "spriteName": None,
                "value": 0,
                "width": 0,
                "height": 0,
                "x": 5,
                "y": 5,
                "visible": False,
                "sliderMin": 0,
                "sliderMax": 100,
                "isDiscrete": True,
            }
        ],
        "extensions": [],
        "meta": {"semver": "3.0.0", "vm": "0.2.0", "agent": "test"},
    }


@pytest.fixture
def minimal_project_data():
    """Return a minimal valid project dict."""
    return _minimal_project_data()


@pytest.fixture
def minimal_project_dir(tmp_path: Path):
    """Create a minimal project directory with project.json and dummy asset files."""
    data = _minimal_project_data()
    project_json = tmp_path / "project.json"
    project_json.write_text(json.dumps(data), encoding="utf-8")

    # Create dummy asset files
    (tmp_path / "cd21514d0531fdffb22204e0ec5ed84a.svg").write_text("<svg/>")
    (tmp_path / "83a9787d4cb6f3b7632b4ddfebf74367.wav").write_bytes(b"\x00" * 100)
    (tmp_path / "bcf454acf82e4504149f7ffe07081dbc.svg").write_text("<svg/>")

    return tmp_path


@pytest.fixture
def minimal_sb3(tmp_path: Path, minimal_project_dir: Path):
    """Create a minimal .sb3 file from the minimal project directory."""
    sb3_path = tmp_path / "test.sb3"
    with zipfile.ZipFile(sb3_path, "w") as zf:
        for f in minimal_project_dir.iterdir():
            if f.is_file():
                zf.write(f, f.name)
    return sb3_path


@pytest.fixture
def real_project_path():
    """Path to the real LogicGateSimulator project (skip if not available)."""
    path = Path("/Users/grishakhachatryan/Desktop/LogicGateSimulator")
    if not (path / "project.json").exists():
        pytest.skip("Real project not available")
    return path
