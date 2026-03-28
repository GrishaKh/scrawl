"""Mutation operations for Scratch projects."""

from __future__ import annotations

import os
from typing import Any, Optional

from scrawl.errors import ScrawlError, SpriteNotFoundError, VariableNotFoundError
from scrawl.model import ScratchProject


def rename_sprite(project: ScratchProject, old_name: str, new_name: str) -> None:
    """
    Rename a sprite. Updates target name, monitors, and block references
    (clone menus, touching object menus).
    """
    target = project.get_target_by_name(old_name)
    if target is None:
        raise SpriteNotFoundError(f"Sprite not found: '{old_name}'")
    if target.get("isStage"):
        raise ScrawlError("Cannot rename the stage")
    if project.get_target_by_name(new_name) is not None:
        raise ScrawlError(f"A target named '{new_name}' already exists")

    # 1. Update target name
    target["name"] = new_name

    # 2. Update monitors referencing this sprite
    for monitor in project.monitors:
        if monitor.get("spriteName") == old_name:
            monitor["spriteName"] = new_name

    # 3. Update block references (clone/touching menus across ALL targets)
    for t in project.targets:
        for block_id, block in t.get("blocks", {}).items():
            if not isinstance(block, dict):
                continue
            opcode = block.get("opcode", "")
            fields = block.get("fields", {})

            # Clone of menu
            if opcode == "control_create_clone_of_menu":
                if "CLONE_OPTION" in fields:
                    if fields["CLONE_OPTION"][0] == old_name:
                        fields["CLONE_OPTION"][0] = new_name

            # Touching object menu
            if opcode == "sensing_touchingobjectmenu":
                if "TOUCHINGOBJECTMENU" in fields:
                    if fields["TOUCHINGOBJECTMENU"][0] == old_name:
                        fields["TOUCHINGOBJECTMENU"][0] = new_name

            # Go to menu
            if opcode == "motion_goto_menu":
                if "TO" in fields:
                    if fields["TO"][0] == old_name:
                        fields["TO"][0] = new_name

            # Glide to menu
            if opcode == "motion_glideto_menu":
                if "TO" in fields:
                    if fields["TO"][0] == old_name:
                        fields["TO"][0] = new_name

            # Point towards menu
            if opcode == "motion_pointtowards_menu":
                if "TOWARDS" in fields:
                    if fields["TOWARDS"][0] == old_name:
                        fields["TOWARDS"][0] = new_name

            # Distance to menu
            if opcode == "sensing_distancetomenu":
                if "DISTANCETOMENU" in fields:
                    if fields["DISTANCETOMENU"][0] == old_name:
                        fields["DISTANCETOMENU"][0] = new_name

            # Of object menu (sensing_of)
            if opcode == "sensing_of_object_menu":
                if "OBJECT" in fields:
                    if fields["OBJECT"][0] == old_name:
                        fields["OBJECT"][0] = new_name


def rename_variable(
    project: ScratchProject,
    old_name: str,
    new_name: str,
    sprite_name: Optional[str] = None,
) -> None:
    """
    Rename a variable or list. Updates the variable/list entry,
    all block fields and inputs referencing it, and monitors.
    """
    # Find the variable
    found_target = None
    found_id = None
    found_type = None  # "variable" or "list"

    search_targets = []
    if sprite_name:
        t = project.get_target_by_name(sprite_name)
        if t is None:
            raise SpriteNotFoundError(f"Sprite not found: '{sprite_name}'")
        search_targets = [t]
    else:
        # Search stage first, then sprites
        if project.stage:
            search_targets.append(project.stage)
        search_targets.extend(project.sprites)

    for t in search_targets:
        # Check variables
        for var_id, var_data in t.get("variables", {}).items():
            if isinstance(var_data, list) and len(var_data) >= 2 and var_data[0] == old_name:
                found_target = t
                found_id = var_id
                found_type = "variable"
                break
        if found_id:
            break
        # Check lists
        for list_id, list_data in t.get("lists", {}).items():
            if isinstance(list_data, list) and len(list_data) >= 2 and list_data[0] == old_name:
                found_target = t
                found_id = list_id
                found_type = "list"
                break
        if found_id:
            break

    if found_id is None:
        scope = f" in sprite '{sprite_name}'" if sprite_name else ""
        raise VariableNotFoundError(f"Variable or list '{old_name}' not found{scope}")

    # 1. Update the variable/list entry name
    if found_type == "variable":
        found_target["variables"][found_id][0] = new_name
    else:
        found_target["lists"][found_id][0] = new_name

    # 2. Update block fields and inputs across ALL targets
    field_key = "VARIABLE" if found_type == "variable" else "LIST"
    type_code = 12 if found_type == "variable" else 13

    for t in project.targets:
        for block_id, block in t.get("blocks", {}).items():
            if not isinstance(block, dict):
                continue

            # Update fields
            fields = block.get("fields", {})
            if field_key in fields:
                field_val = fields[field_key]
                if isinstance(field_val, list) and len(field_val) >= 2:
                    if field_val[1] == found_id:
                        field_val[0] = new_name

            # Update input arrays containing [type_code, name, id, ...]
            for input_name, input_val in block.get("inputs", {}).items():
                if not isinstance(input_val, list):
                    continue
                _update_var_in_input(input_val, found_id, new_name, type_code)

    # 3. Update monitors
    param_key = "VARIABLE" if found_type == "variable" else "LIST"
    for monitor in project.monitors:
        params = monitor.get("params", {})
        if params.get(param_key) == old_name:
            params[param_key] = new_name


def _update_var_in_input(
    input_val: list, var_id: str, new_name: str, type_code: int
) -> None:
    """Update variable/list name in input arrays recursively."""
    for item in input_val:
        if isinstance(item, list) and len(item) >= 3:
            if item[0] == type_code and item[2] == var_id:
                item[1] = new_name


def delete_sprite(project: ScratchProject, sprite_name: str) -> list[str]:
    """
    Remove a sprite and its exclusive assets.
    Returns list of deleted asset filenames.
    """
    target = project.get_target_by_name(sprite_name)
    if target is None:
        raise SpriteNotFoundError(f"Sprite not found: '{sprite_name}'")
    if target.get("isStage"):
        raise ScrawlError("Cannot delete the stage")

    # 1. Collect this sprite's assets
    sprite_assets: set[str] = set()
    for costume in target.get("costumes", []):
        md5ext = costume.get("md5ext", "")
        if md5ext:
            sprite_assets.add(md5ext)
    for sound in target.get("sounds", []):
        md5ext = sound.get("md5ext", "")
        if md5ext:
            sprite_assets.add(md5ext)

    # 2. Find assets used by OTHER targets
    shared_assets: set[str] = set()
    for t in project.targets:
        if t.get("name") == sprite_name:
            continue
        for costume in t.get("costumes", []):
            md5ext = costume.get("md5ext", "")
            if md5ext in sprite_assets:
                shared_assets.add(md5ext)
        for sound in t.get("sounds", []):
            md5ext = sound.get("md5ext", "")
            if md5ext in sprite_assets:
                shared_assets.add(md5ext)

    exclusive_assets = sprite_assets - shared_assets

    # 3. Remove target from targets list
    project.raw["targets"] = [
        t for t in project.targets if t.get("name") != sprite_name
    ]

    # 4. Remove monitors for this sprite
    project.raw["monitors"] = [
        m for m in project.monitors if m.get("spriteName") != sprite_name
    ]

    # 5. Delete exclusive asset files from disk
    deleted = []
    if project.base_path:
        for md5ext in exclusive_assets:
            asset_path = project.base_path / md5ext
            if asset_path.exists():
                os.remove(asset_path)
                deleted.append(md5ext)
    else:
        deleted = list(exclusive_assets)

    # 6. Clean up clone-of references pointing to this sprite
    for t in project.targets:
        for block_id, block in t.get("blocks", {}).items():
            if not isinstance(block, dict):
                continue
            if block.get("opcode") == "control_create_clone_of_menu":
                fields = block.get("fields", {})
                if "CLONE_OPTION" in fields and fields["CLONE_OPTION"][0] == sprite_name:
                    fields["CLONE_OPTION"][0] = "_myself_"

    return sorted(deleted)


def set_meta(project: ScratchProject, key: str, value: str) -> None:
    """Set a metadata field. Only allows known meta keys."""
    allowed_keys = {"semver", "vm", "agent"}
    if key not in allowed_keys:
        raise ScrawlError(
            f"Unknown meta key: '{key}'. Allowed keys: {', '.join(sorted(allowed_keys))}"
        )
    if "meta" not in project.raw:
        project.raw["meta"] = {}
    project.raw["meta"][key] = value
