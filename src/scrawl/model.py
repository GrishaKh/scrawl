"""Core project model — thin wrapper over the raw project.json dict."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, Optional

from scrawl.errors import InvalidProjectError, ProjectNotFoundError


@dataclass
class ValidationIssue:
    """A single validation problem found in the project."""

    severity: str  # "error" or "warning"
    category: str  # e.g., "asset", "block", "variable", "structure"
    message: str
    target_name: Optional[str] = None
    block_id: Optional[str] = None


class ScratchProject:
    """
    Thin wrapper around the raw project.json dict.

    Provides typed accessors and mutation methods while preserving
    the full JSON structure for lossless round-tripping.
    """

    def __init__(self, data: dict[str, Any], base_path: Optional[Path] = None):
        self._data = data
        self.base_path = base_path

    @classmethod
    def from_json_string(
        cls, text: str, base_path: Optional[Path] = None
    ) -> ScratchProject:
        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            raise InvalidProjectError(f"Invalid JSON: {e}") from e
        if not isinstance(data, dict):
            raise InvalidProjectError("project.json root must be a JSON object")
        return cls(data, base_path)

    @classmethod
    def from_file(cls, path: Path) -> ScratchProject:
        path = Path(path)
        if not path.exists():
            raise ProjectNotFoundError(f"File not found: {path}")
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as e:
            raise ProjectNotFoundError(f"Cannot read {path}: {e}") from e
        return cls.from_json_string(text, base_path=path.parent)

    def to_json_string(self, indent: Optional[int] = None) -> str:
        return json.dumps(self._data, indent=indent, ensure_ascii=False)

    def save(self, path: Optional[Path] = None) -> None:
        if path is None:
            if self.base_path is None:
                raise ScrawlError("No base_path set and no path provided")
            path = self.base_path / "project.json"
        path = Path(path)
        path.write_text(self.to_json_string(), encoding="utf-8")

    # --- Accessors ---

    @property
    def raw(self) -> dict[str, Any]:
        return self._data

    @property
    def targets(self) -> list[dict[str, Any]]:
        return self._data.get("targets", [])

    @property
    def stage(self) -> Optional[dict[str, Any]]:
        for t in self.targets:
            if t.get("isStage"):
                return t
        return None

    @property
    def sprites(self) -> list[dict[str, Any]]:
        return [t for t in self.targets if not t.get("isStage")]

    def get_target_by_name(self, name: str) -> Optional[dict[str, Any]]:
        for t in self.targets:
            if t.get("name") == name:
                return t
        return None

    @property
    def extensions(self) -> list[str]:
        return self._data.get("extensions", [])

    @property
    def meta(self) -> dict[str, Any]:
        return self._data.get("meta", {})

    @property
    def monitors(self) -> list[dict[str, Any]]:
        return self._data.get("monitors", [])

    # --- Iterators ---

    def all_variables(self) -> Iterator[tuple[str, str, str, Any]]:
        """Yields (target_name, var_id, var_name, var_value) for every variable."""
        for target in self.targets:
            target_name = target.get("name", "")
            for var_id, var_data in target.get("variables", {}).items():
                if isinstance(var_data, list) and len(var_data) >= 2:
                    yield (target_name, var_id, var_data[0], var_data[1])

    def all_lists(self) -> Iterator[tuple[str, str, str, list]]:
        """Yields (target_name, list_id, list_name, list_value) for every list."""
        for target in self.targets:
            target_name = target.get("name", "")
            for list_id, list_data in target.get("lists", {}).items():
                if isinstance(list_data, list) and len(list_data) >= 2:
                    yield (target_name, list_id, list_data[0], list_data[1])

    def all_blocks(self) -> Iterator[tuple[str, str, dict[str, Any]]]:
        """Yields (target_name, block_id, block_dict) for every dict-form block."""
        for target in self.targets:
            target_name = target.get("name", "")
            for block_id, block in target.get("blocks", {}).items():
                if isinstance(block, dict):
                    yield (target_name, block_id, block)

    def all_assets_referenced(self) -> Iterator[tuple[str, str, str, str]]:
        """Yields (target_name, asset_type, asset_name, md5ext) for every costume and sound."""
        for target in self.targets:
            target_name = target.get("name", "")
            for costume in target.get("costumes", []):
                yield (
                    target_name,
                    "costume",
                    costume.get("name", ""),
                    costume.get("md5ext", ""),
                )
            for sound in target.get("sounds", []):
                yield (
                    target_name,
                    "sound",
                    sound.get("name", ""),
                    sound.get("md5ext", ""),
                )
