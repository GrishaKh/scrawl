"""Read-only query functions for inspecting Scratch projects."""

from __future__ import annotations

import os
from collections import Counter
from typing import Any

from scrawl.model import ScratchProject

# Built-in opcode categories (not extensions)
BUILTIN_CATEGORIES = frozenset(
    {
        "motion",
        "looks",
        "sound",
        "event",
        "control",
        "sensing",
        "operator",
        "data",
        "procedures",
        "argument",
    }
)


def get_project_info(project: ScratchProject) -> dict[str, Any]:
    """Return a summary of the project."""
    total_blocks = 0
    total_costumes = 0
    total_sounds = 0
    total_variables = 0
    total_lists = 0

    for target in project.targets:
        blocks = target.get("blocks", {})
        total_blocks += sum(1 for b in blocks.values() if isinstance(b, dict))
        total_costumes += len(target.get("costumes", []))
        total_sounds += len(target.get("sounds", []))
        total_variables += len(target.get("variables", {}))
        total_lists += len(target.get("lists", {}))

    return {
        "sprite_count": len(project.sprites),
        "variable_count": total_variables,
        "list_count": total_lists,
        "block_count": total_blocks,
        "costume_count": total_costumes,
        "sound_count": total_sounds,
        "monitor_count": len(project.monitors),
        "extensions": project.extensions,
        "meta": project.meta,
    }


def get_sprites(project: ScratchProject) -> list[dict[str, Any]]:
    """Return per-sprite details."""
    result = []
    for target in project.targets:
        blocks = target.get("blocks", {})
        block_count = sum(1 for b in blocks.values() if isinstance(b, dict))
        top_level_count = sum(
            1
            for b in blocks.values()
            if isinstance(b, dict) and b.get("topLevel")
        )
        entry = {
            "name": target.get("name", ""),
            "is_stage": target.get("isStage", False),
            "x": target.get("x", 0),
            "y": target.get("y", 0),
            "size": target.get("size", 100),
            "direction": target.get("direction", 90),
            "visible": target.get("visible", True),
            "draggable": target.get("draggable", False),
            "rotation_style": target.get("rotationStyle", "all around"),
            "layer_order": target.get("layerOrder", 0),
            "costume_count": len(target.get("costumes", [])),
            "sound_count": len(target.get("sounds", [])),
            "block_count": block_count,
            "top_level_count": top_level_count,
            "variable_count": len(target.get("variables", {})),
            "list_count": len(target.get("lists", {})),
            "current_costume": target.get("currentCostume", 0),
        }
        result.append(entry)
    return result


def get_variables(project: ScratchProject) -> list[dict[str, Any]]:
    """Return all variables and lists across all targets."""
    result = []

    for target_name, var_id, var_name, var_value in project.all_variables():
        is_stage = any(
            t.get("name") == target_name and t.get("isStage")
            for t in project.targets
        )
        result.append(
            {
                "name": var_name,
                "id": var_id,
                "scope": "global" if is_stage else target_name,
                "type": "variable",
                "value": var_value,
            }
        )

    for target_name, list_id, list_name, list_value in project.all_lists():
        is_stage = any(
            t.get("name") == target_name and t.get("isStage")
            for t in project.targets
        )
        result.append(
            {
                "name": list_name,
                "id": list_id,
                "scope": "global" if is_stage else target_name,
                "type": "list",
                "length": len(list_value) if isinstance(list_value, list) else 0,
            }
        )

    return result


def get_block_stats(project: ScratchProject) -> dict[str, Any]:
    """Return block statistics by category and opcode."""
    by_opcode: Counter = Counter()
    top_level_count = 0

    for _target_name, _block_id, block in project.all_blocks():
        opcode = block.get("opcode", "unknown")
        by_opcode[opcode] += 1
        if block.get("topLevel"):
            top_level_count += 1

    # Group by category (opcode prefix before first _)
    by_category: Counter = Counter()
    for opcode, count in by_opcode.items():
        parts = opcode.split("_", 1)
        category = parts[0] if parts else "unknown"
        by_category[category] += count

    return {
        "total_blocks": sum(by_opcode.values()),
        "top_level_stacks": top_level_count,
        "by_category": dict(by_category.most_common()),
        "by_opcode": dict(by_opcode.most_common()),
    }


def get_assets(project: ScratchProject) -> list[dict[str, Any]]:
    """Return all referenced assets with file info."""
    seen = set()
    result = []

    for target_name, asset_type, asset_name, md5ext in project.all_assets_referenced():
        if not md5ext:
            continue

        # Determine file existence and size
        file_exists = None
        file_size = None

        if project.base_path is not None:
            asset_path = project.base_path / md5ext
            file_exists = asset_path.exists()
            if file_exists:
                file_size = os.path.getsize(asset_path)
        elif hasattr(project, "_zip_names"):
            file_exists = md5ext in project._zip_names

        # Determine data format from md5ext
        data_format = md5ext.rsplit(".", 1)[-1] if "." in md5ext else "unknown"

        entry = {
            "md5ext": md5ext,
            "name": asset_name,
            "type": asset_type,
            "data_format": data_format,
            "target_name": target_name,
            "file_exists": file_exists,
            "file_size": file_size,
        }

        # Track unique assets for dedup reporting
        if md5ext not in seen:
            entry["unique"] = True
            seen.add(md5ext)
        else:
            entry["unique"] = False

        result.append(entry)

    return result


def get_project_tree(project: ScratchProject) -> dict[str, Any]:
    """Return hierarchical project structure for tree rendering."""
    targets_tree = []

    for target in project.targets:
        blocks = target.get("blocks", {})
        block_count = sum(1 for b in blocks.values() if isinstance(b, dict))
        top_level = sum(
            1 for b in blocks.values() if isinstance(b, dict) and b.get("topLevel")
        )

        costumes = [
            {"name": c.get("name", ""), "md5ext": c.get("md5ext", "")}
            for c in target.get("costumes", [])
        ]
        sounds = [
            {"name": s.get("name", ""), "md5ext": s.get("md5ext", "")}
            for s in target.get("sounds", [])
        ]
        variables = [
            {"name": v[0], "value": v[1]}
            for v in target.get("variables", {}).values()
            if isinstance(v, list) and len(v) >= 2
        ]
        lists = [
            {"name": l[0], "length": len(l[1]) if isinstance(l[1], list) else 0}
            for l in target.get("lists", {}).values()
            if isinstance(l, list) and len(l) >= 2
        ]

        targets_tree.append(
            {
                "name": target.get("name", ""),
                "is_stage": target.get("isStage", False),
                "costumes": costumes,
                "sounds": sounds,
                "variables": variables,
                "lists": lists,
                "block_count": block_count,
                "top_level_stacks": top_level,
            }
        )

    stage_name = project.stage.get("name", "Stage") if project.stage else "Stage"
    return {
        "name": stage_name,
        "extensions": project.extensions,
        "targets": targets_tree,
    }
