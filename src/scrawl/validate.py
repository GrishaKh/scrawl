"""Validation engine for Scratch 3.0 projects."""

from __future__ import annotations

import re
from typing import Any

from scrawl.model import ScratchProject, ValidationIssue

# Built-in opcode prefixes that don't need to be in the extensions array
BUILTIN_OPCODE_PREFIXES = frozenset(
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

# Valid enum values from the Scratch 3.0 spec (scratch-parser sb3_definitions.json)
VALID_COSTUME_FORMATS = frozenset({"png", "svg", "jpeg", "jpg", "bmp", "gif"})
VALID_SOUND_FORMATS = frozenset({"wav", "wave", "mp3"})
VALID_ROTATION_STYLES = frozenset({"all around", "don't rotate", "left-right"})
VALID_VIDEO_STATES = frozenset({"on", "off", "on-flipped"})
ASSET_ID_RE = re.compile(r"^[a-fA-F0-9]{32}$")
SEMVER_RE = re.compile(r"^3\.\d+\.\d+$")
MAX_COMMENT_LENGTH = 8000


def validate_project(project: ScratchProject) -> list[ValidationIssue]:
    """Run all validation checks and return a list of issues."""
    issues: list[ValidationIssue] = []
    issues.extend(_check_json_structure(project))
    issues.extend(_check_stage_is_first(project))
    issues.extend(_check_costumes_exist(project))
    issues.extend(_check_assets_on_disk(project))
    issues.extend(_check_block_references(project))
    issues.extend(_check_variable_references(project))
    issues.extend(_check_extension_declarations(project))
    issues.extend(_check_costume_indices(project))
    issues.extend(_check_meta_semver(project))
    issues.extend(_check_stage_constraints(project))
    issues.extend(_check_sprite_constraints(project))
    issues.extend(_check_asset_formats(project))
    issues.extend(_check_block_opcodes(project))
    issues.extend(_check_comments(project))
    return issues


def _check_json_structure(project: ScratchProject) -> list[ValidationIssue]:
    issues = []
    if "targets" not in project.raw:
        issues.append(
            ValidationIssue("error", "structure", "Missing 'targets' key in project.json")
        )
    elif not isinstance(project.raw["targets"], list) or len(project.raw["targets"]) == 0:
        issues.append(
            ValidationIssue("error", "structure", "'targets' must be a non-empty array")
        )
    if "meta" not in project.raw:
        issues.append(
            ValidationIssue("warning", "structure", "Missing 'meta' key in project.json")
        )
    return issues


def _check_stage_is_first(project: ScratchProject) -> list[ValidationIssue]:
    issues = []
    targets = project.targets
    if targets and not targets[0].get("isStage"):
        issues.append(
            ValidationIssue(
                "error",
                "structure",
                f"First target '{targets[0].get('name', '?')}' must have isStage: true",
            )
        )
    return issues


def _check_costumes_exist(project: ScratchProject) -> list[ValidationIssue]:
    issues = []
    for target in project.targets:
        name = target.get("name", "?")
        costumes = target.get("costumes", [])
        if not costumes:
            issues.append(
                ValidationIssue(
                    "error", "structure", "Target has no costumes", target_name=name
                )
            )
    return issues


def _check_assets_on_disk(project: ScratchProject) -> list[ValidationIssue]:
    issues = []
    # Determine available files
    available: set[str] | None = None
    if project.base_path is not None:
        available = {f.name for f in project.base_path.iterdir() if f.is_file()}
    elif hasattr(project, "_zip_names"):
        available = project._zip_names

    if available is None:
        return issues  # Can't check without file access

    for target_name, asset_type, asset_name, md5ext in project.all_assets_referenced():
        if not md5ext:
            continue
        if md5ext not in available:
            issues.append(
                ValidationIssue(
                    "error",
                    "asset",
                    f"Missing {asset_type} file: {md5ext} ('{asset_name}')",
                    target_name=target_name,
                )
            )
    return issues


def _check_block_references(project: ScratchProject) -> list[ValidationIssue]:
    issues = []
    for target in project.targets:
        target_name = target.get("name", "?")
        blocks = target.get("blocks", {})
        block_ids = set(blocks.keys())

        for block_id, block in blocks.items():
            if not isinstance(block, dict):
                continue

            # Check next reference
            next_id = block.get("next")
            if next_id is not None and next_id not in block_ids:
                issues.append(
                    ValidationIssue(
                        "error",
                        "block",
                        f"Block 'next' references non-existent block: {next_id}",
                        target_name=target_name,
                        block_id=block_id,
                    )
                )

            # Check parent reference
            parent_id = block.get("parent")
            if parent_id is not None and parent_id not in block_ids:
                issues.append(
                    ValidationIssue(
                        "error",
                        "block",
                        f"Block 'parent' references non-existent block: {parent_id}",
                        target_name=target_name,
                        block_id=block_id,
                    )
                )

            # Check input references
            for input_name, input_val in block.get("inputs", {}).items():
                if not isinstance(input_val, list) or len(input_val) < 2:
                    continue
                _check_input_block_ref(
                    input_val, block_ids, issues, target_name, block_id, input_name
                )

    return issues


def _check_input_block_ref(
    input_val: list,
    block_ids: set[str],
    issues: list[ValidationIssue],
    target_name: str,
    block_id: str,
    input_name: str,
) -> None:
    """Check that block ID references in an input array are valid."""
    shadow_type = input_val[0]
    value = input_val[1]

    # Shadow type 2 or 3: position [1] is a block ID string (or an array for primitives)
    if shadow_type in (2, 3) and isinstance(value, str) and value not in block_ids:
        issues.append(
            ValidationIssue(
                "error",
                "block",
                f"Input '{input_name}' references non-existent block: {value}",
                target_name=target_name,
                block_id=block_id,
            )
        )

    # Shadow type 1: value could be a block ID string or a literal array
    if shadow_type == 1 and isinstance(value, str) and value not in block_ids:
        issues.append(
            ValidationIssue(
                "error",
                "block",
                f"Input '{input_name}' references non-existent block: {value}",
                target_name=target_name,
                block_id=block_id,
            )
        )

    # Shadow type 3: position [2] might also be a block ID
    if shadow_type == 3 and len(input_val) >= 3:
        shadow_val = input_val[2]
        if isinstance(shadow_val, str) and shadow_val not in block_ids:
            issues.append(
                ValidationIssue(
                    "error",
                    "block",
                    f"Input '{input_name}' shadow references non-existent block: {shadow_val}",
                    target_name=target_name,
                    block_id=block_id,
                )
            )


def _check_variable_references(project: ScratchProject) -> list[ValidationIssue]:
    issues = []
    stage_vars = {}
    stage_lists = {}

    if project.stage:
        stage_vars = set(project.stage.get("variables", {}).keys())
        stage_lists = set(project.stage.get("lists", {}).keys())

    for target in project.targets:
        target_name = target.get("name", "?")
        local_vars = set(target.get("variables", {}).keys())
        local_lists = set(target.get("lists", {}).keys())
        all_vars = local_vars | stage_vars
        all_lists = local_lists | stage_lists

        for block_id, block in target.get("blocks", {}).items():
            if not isinstance(block, dict):
                continue

            # Check VARIABLE fields
            fields = block.get("fields", {})
            if "VARIABLE" in fields:
                field_val = fields["VARIABLE"]
                if isinstance(field_val, list) and len(field_val) >= 2:
                    var_id = field_val[1]
                    if var_id and var_id not in all_vars:
                        issues.append(
                            ValidationIssue(
                                "error",
                                "variable",
                                f"VARIABLE field references unknown variable ID: {var_id} ('{field_val[0]}')",
                                target_name=target_name,
                                block_id=block_id,
                            )
                        )

            if "LIST" in fields:
                field_val = fields["LIST"]
                if isinstance(field_val, list) and len(field_val) >= 2:
                    list_id = field_val[1]
                    if list_id and list_id not in all_lists:
                        issues.append(
                            ValidationIssue(
                                "error",
                                "variable",
                                f"LIST field references unknown list ID: {list_id} ('{field_val[0]}')",
                                target_name=target_name,
                                block_id=block_id,
                            )
                        )

            # Check input arrays for type 12 (variable) and type 13 (list) references
            for input_name, input_val in block.get("inputs", {}).items():
                if not isinstance(input_val, list):
                    continue
                _check_var_in_input(
                    input_val, all_vars, all_lists, issues, target_name, block_id
                )

    return issues


def _check_var_in_input(
    input_val: list,
    all_vars: set,
    all_lists: set,
    issues: list[ValidationIssue],
    target_name: str,
    block_id: str,
) -> None:
    """Check for type 12/13 variable/list references in input arrays."""
    for item in input_val:
        if not isinstance(item, list) or len(item) < 3:
            continue
        type_code = item[0]
        ref_name = item[1]
        ref_id = item[2]

        if type_code == 12 and ref_id not in all_vars:
            issues.append(
                ValidationIssue(
                    "error",
                    "variable",
                    f"Input references unknown variable: '{ref_name}' (ID: {ref_id})",
                    target_name=target_name,
                    block_id=block_id,
                )
            )
        elif type_code == 13 and ref_id not in all_lists:
            issues.append(
                ValidationIssue(
                    "error",
                    "variable",
                    f"Input references unknown list: '{ref_name}' (ID: {ref_id})",
                    target_name=target_name,
                    block_id=block_id,
                )
            )


def _check_extension_declarations(project: ScratchProject) -> list[ValidationIssue]:
    issues = []
    declared = set(project.extensions)
    used_prefixes: set[str] = set()

    for _target_name, _block_id, block in project.all_blocks():
        opcode = block.get("opcode", "")
        prefix = opcode.split("_", 1)[0] if "_" in opcode else ""
        if prefix and prefix not in BUILTIN_OPCODE_PREFIXES:
            used_prefixes.add(prefix)

    for prefix in used_prefixes:
        if prefix not in declared:
            issues.append(
                ValidationIssue(
                    "warning",
                    "extension",
                    f"Extension '{prefix}' is used in blocks but not declared in extensions array",
                )
            )

    return issues


def _check_costume_indices(project: ScratchProject) -> list[ValidationIssue]:
    issues = []
    for target in project.targets:
        name = target.get("name", "?")
        idx = target.get("currentCostume", 0)
        costumes = target.get("costumes", [])
        if not isinstance(idx, int) or idx < 0 or idx >= len(costumes):
            issues.append(
                ValidationIssue(
                    "error",
                    "structure",
                    f"currentCostume index {idx} is out of range [0, {len(costumes)})",
                    target_name=name,
                )
            )
    return issues


def _check_meta_semver(project: ScratchProject) -> list[ValidationIssue]:
    issues = []
    meta = project.raw.get("meta", {})
    if not isinstance(meta, dict):
        return issues
    semver = meta.get("semver", "")
    if semver and not SEMVER_RE.match(semver):
        issues.append(
            ValidationIssue(
                "warning",
                "structure",
                f"meta.semver '{semver}' does not match expected format '3.X.Y'",
            )
        )
    return issues


def _check_stage_constraints(project: ScratchProject) -> list[ValidationIssue]:
    issues = []
    stage = project.stage
    if not stage:
        return issues

    name = stage.get("name", "")
    if name != "Stage":
        issues.append(
            ValidationIssue(
                "warning",
                "structure",
                f"Stage target name is '{name}', expected 'Stage'",
                target_name=name,
            )
        )

    layer = stage.get("layerOrder")
    if layer is not None and layer != 0:
        issues.append(
            ValidationIssue(
                "warning",
                "structure",
                f"Stage layerOrder is {layer}, expected 0",
                target_name=name,
            )
        )

    video_state = stage.get("videoState")
    if video_state is not None and video_state not in VALID_VIDEO_STATES:
        issues.append(
            ValidationIssue(
                "warning",
                "structure",
                f"Stage videoState '{video_state}' not in {sorted(VALID_VIDEO_STATES)}",
                target_name=name,
            )
        )

    return issues


def _check_sprite_constraints(project: ScratchProject) -> list[ValidationIssue]:
    issues = []
    for target in project.targets:
        if target.get("isStage"):
            continue

        name = target.get("name", "?")

        if name == "_stage_":
            issues.append(
                ValidationIssue(
                    "error",
                    "structure",
                    "Sprite name '_stage_' is reserved",
                    target_name=name,
                )
            )

        layer = target.get("layerOrder")
        if layer is not None and (not isinstance(layer, int) or layer < 1):
            issues.append(
                ValidationIssue(
                    "warning",
                    "structure",
                    f"Sprite layerOrder is {layer}, expected >= 1",
                    target_name=name,
                )
            )

        rot = target.get("rotationStyle")
        if rot is not None and rot not in VALID_ROTATION_STYLES:
            issues.append(
                ValidationIssue(
                    "warning",
                    "structure",
                    f"rotationStyle '{rot}' not in {sorted(VALID_ROTATION_STYLES)}",
                    target_name=name,
                )
            )

    return issues


def _check_asset_formats(project: ScratchProject) -> list[ValidationIssue]:
    issues = []
    for target in project.targets:
        name = target.get("name", "?")

        for costume in target.get("costumes", []):
            asset_id = costume.get("assetId", "")
            if asset_id and not ASSET_ID_RE.match(asset_id):
                issues.append(
                    ValidationIssue(
                        "error",
                        "asset",
                        f"Costume '{costume.get('name', '?')}' assetId '{asset_id}' is not valid 32-char hex",
                        target_name=name,
                    )
                )

            fmt = costume.get("dataFormat", "")
            if fmt and fmt not in VALID_COSTUME_FORMATS:
                issues.append(
                    ValidationIssue(
                        "error",
                        "asset",
                        f"Costume '{costume.get('name', '?')}' dataFormat '{fmt}' not in {sorted(VALID_COSTUME_FORMATS)}",
                        target_name=name,
                    )
                )

        for sound in target.get("sounds", []):
            asset_id = sound.get("assetId", "")
            if asset_id and not ASSET_ID_RE.match(asset_id):
                issues.append(
                    ValidationIssue(
                        "error",
                        "asset",
                        f"Sound '{sound.get('name', '?')}' assetId '{asset_id}' is not valid 32-char hex",
                        target_name=name,
                    )
                )

            fmt = sound.get("dataFormat", "")
            if fmt and fmt not in VALID_SOUND_FORMATS:
                issues.append(
                    ValidationIssue(
                        "error",
                        "asset",
                        f"Sound '{sound.get('name', '?')}' dataFormat '{fmt}' not in {sorted(VALID_SOUND_FORMATS)}",
                        target_name=name,
                    )
                )

    return issues


def _check_block_opcodes(project: ScratchProject) -> list[ValidationIssue]:
    issues = []
    for target_name, block_id, block in project.all_blocks():
        if not isinstance(block, dict):
            continue
        if "opcode" not in block:
            issues.append(
                ValidationIssue(
                    "error",
                    "block",
                    "Block is missing required 'opcode' field",
                    target_name=target_name,
                    block_id=block_id,
                )
            )
    return issues


def _check_comments(project: ScratchProject) -> list[ValidationIssue]:
    issues = []
    for target in project.targets:
        name = target.get("name", "?")
        for comment_id, comment in target.get("comments", {}).items():
            if not isinstance(comment, dict):
                continue
            text = comment.get("text", "")
            if isinstance(text, str) and len(text) > MAX_COMMENT_LENGTH:
                issues.append(
                    ValidationIssue(
                        "warning",
                        "structure",
                        f"Comment text exceeds {MAX_COMMENT_LENGTH} characters ({len(text)} chars)",
                        target_name=name,
                    )
                )
    return issues
