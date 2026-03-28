"""Decompiler — convert Scratch block JSON back to readable .scr text.

Walks the block graph for a target and reconstructs human-readable
ScratchText source that can be re-compiled back to blocks.
"""

from __future__ import annotations

import json
from typing import Any, Optional

from scrawl.compiler.registry import BlockShape
from scrawl.compiler.registry_data import ALL_BLOCKS

# ---------------------------------------------------------------------------
# Reverse lookup tables
# ---------------------------------------------------------------------------

# opcode → list of BlockDef (some opcodes have multiple patterns, e.g. costume number/name)
_OPCODE_TO_DEFS: dict[str, list] = {}
for _bd in ALL_BLOCKS:
    _OPCODE_TO_DEFS.setdefault(_bd.opcode, []).append(_bd)

# Opcodes that are C-blocks (have substacks)
_C_BLOCK_OPCODES = frozenset(
    bd.opcode for bd in ALL_BLOCKS if bd.shape == BlockShape.C_BLOCK
)

# Opcodes that are boolean reporters
_BOOLEAN_OPCODES = frozenset(
    bd.opcode for bd in ALL_BLOCKS if bd.shape == BlockShape.BOOLEAN
)

# Opcodes that are reporter blocks (non-boolean)
_REPORTER_OPCODES = frozenset(
    bd.opcode for bd in ALL_BLOCKS if bd.shape == BlockShape.REPORTER
)

# Hat opcodes
_HAT_OPCODES = frozenset(
    bd.opcode for bd in ALL_BLOCKS if bd.shape == BlockShape.HAT
)

# Primitive type codes → human readable
_PRIM_NUMBER_TYPES = {4, 5, 6, 7, 8}  # number, positive_number, etc.
_PRIM_STRING_TYPE = 10
_PRIM_BROADCAST_TYPE = 11
_PRIM_VARIABLE_TYPE = 12
_PRIM_LIST_TYPE = 13
_PRIM_COLOR_TYPE = 9


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def decompile_target(target: dict[str, Any]) -> str:
    """Decompile all scripts in a target to .scr text.

    Args:
        target: A target dict (sprite or stage) containing a "blocks" key.

    Returns:
        The decompiled .scr source text.
    """
    blocks = target.get("blocks", {})
    if not blocks:
        return ""

    # Find all top-level blocks and sort by y position for consistent ordering
    top_level_ids = [
        bid for bid, b in blocks.items()
        if isinstance(b, dict) and b.get("topLevel", False)
    ]
    top_level_ids.sort(key=lambda bid: (blocks[bid].get("y", 0), blocks[bid].get("x", 0)))

    scripts: list[str] = []

    for top_id in top_level_ids:
        block = blocks[top_id]
        opcode = block.get("opcode", "")

        # Skip shadow blocks and non-hat/non-definition blocks at top level
        if block.get("shadow", False):
            continue

        if opcode == "procedures_definition":
            script_text = _decompile_custom_def(blocks, top_id)
        elif opcode in _HAT_OPCODES:
            script_text = _decompile_hat_script(blocks, top_id)
        else:
            # Orphan top-level block (rare but possible)
            script_text = _decompile_chain(blocks, top_id, indent=0)

        if script_text.strip():
            scripts.append(script_text)

    return "\n\n".join(scripts) + "\n" if scripts else ""


# ---------------------------------------------------------------------------
# Script decompilation
# ---------------------------------------------------------------------------


def _decompile_hat_script(blocks: dict, hat_id: str) -> str:
    """Decompile a script starting with a hat block."""
    lines: list[str] = []

    hat_line = _decompile_block_line(blocks, hat_id)
    lines.append(hat_line)

    # Follow the chain from hat's next
    next_id = blocks[hat_id].get("next")
    if next_id:
        body = _decompile_chain(blocks, next_id, indent=0)
        if body:
            lines.append(body)

    return "\n".join(lines)


def _decompile_custom_def(blocks: dict, def_id: str) -> str:
    """Decompile a custom block definition."""
    lines: list[str] = []
    block = blocks[def_id]

    # Find the prototype
    custom_block_input = block.get("inputs", {}).get("custom_block")
    if not custom_block_input:
        return ""

    proto_id = custom_block_input[1]
    proto = blocks.get(proto_id, {})
    mutation = proto.get("mutation", {})

    proccode = mutation.get("proccode", "")
    arg_names = json.loads(mutation.get("argumentnames", "[]"))
    arg_types = []

    # Infer types from proccode
    parts = proccode.split()
    arg_idx = 0
    define_parts = ["define"]
    for part in parts:
        if part == "%s":
            if arg_idx < len(arg_names):
                define_parts.append(f"({arg_names[arg_idx]})")
            arg_idx += 1
        elif part == "%b":
            if arg_idx < len(arg_names):
                define_parts.append(f"<{arg_names[arg_idx]}>")
            arg_idx += 1
        else:
            define_parts.append(part)

    lines.append(" ".join(define_parts))

    # Body
    next_id = block.get("next")
    if next_id:
        body = _decompile_chain(blocks, next_id, indent=1)
        if body:
            lines.append(body)

    lines.append("end")
    return "\n".join(lines)


def _decompile_chain(blocks: dict, start_id: str, indent: int) -> str:
    """Decompile a chain of statement blocks."""
    lines: list[str] = []
    current_id: Optional[str] = start_id
    prefix = "  " * indent

    while current_id:
        block = blocks.get(current_id)
        if not block or not isinstance(block, dict):
            break

        opcode = block.get("opcode", "")

        if opcode == "control_if_else":
            c_text = _decompile_if_else(blocks, current_id, indent)
            lines.append(c_text)
        elif opcode in _C_BLOCK_OPCODES:
            c_text = _decompile_c_block(blocks, current_id, indent)
            lines.append(c_text)
        else:
            line = _decompile_block_line(blocks, current_id)
            lines.append(f"{prefix}{line}")

        current_id = block.get("next")

    return "\n".join(lines)


def _decompile_c_block(blocks: dict, block_id: str, indent: int) -> str:
    """Decompile a C-block (forever, repeat, if, repeat until)."""
    lines: list[str] = []
    prefix = "  " * indent

    block_line = _decompile_block_line(blocks, block_id)
    lines.append(f"{prefix}{block_line}")

    # Decompile substack
    block = blocks[block_id]
    substack = block.get("inputs", {}).get("SUBSTACK")
    if substack and len(substack) >= 2 and isinstance(substack[1], str):
        body = _decompile_chain(blocks, substack[1], indent + 1)
        if body:
            lines.append(body)

    lines.append(f"{prefix}end")
    return "\n".join(lines)


def _decompile_if_else(blocks: dict, block_id: str, indent: int) -> str:
    """Decompile an if-else block."""
    lines: list[str] = []
    prefix = "  " * indent
    block = blocks[block_id]

    # Use control_if pattern for the header (same: "if <CONDITION> then")
    defs = _OPCODE_TO_DEFS.get("control_if", [])
    if defs:
        block_line = _reconstruct_pattern(blocks, block, defs[0])
    else:
        block_line = _decompile_block_line(blocks, block_id)
    lines.append(f"{prefix}{block_line}")

    # If body (SUBSTACK)
    substack = block.get("inputs", {}).get("SUBSTACK")
    if substack and len(substack) >= 2 and isinstance(substack[1], str):
        body = _decompile_chain(blocks, substack[1], indent + 1)
        if body:
            lines.append(body)

    lines.append(f"{prefix}else")

    # Else body (SUBSTACK2)
    substack2 = block.get("inputs", {}).get("SUBSTACK2")
    if substack2 and len(substack2) >= 2 and isinstance(substack2[1], str):
        body2 = _decompile_chain(blocks, substack2[1], indent + 1)
        if body2:
            lines.append(body2)

    lines.append(f"{prefix}end")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Single block decompilation
# ---------------------------------------------------------------------------


def _decompile_block_line(blocks: dict, block_id: str) -> str:
    """Decompile a single block into its .scr text representation."""
    block = blocks[block_id]
    opcode = block.get("opcode", "")

    # Special case: procedures_call
    if opcode == "procedures_call":
        return _decompile_procedure_call(blocks, block_id)

    # Look up the BlockDef for this opcode
    defs = _OPCODE_TO_DEFS.get(opcode, [])
    if not defs:
        return f"// unknown: {opcode}"

    # Pick the best matching def (use field values to disambiguate variants)
    block_def = _pick_best_def(defs, block)

    return _reconstruct_pattern(blocks, block, block_def)


def _pick_best_def(defs: list, block: dict) -> Any:
    """Pick the best BlockDef when multiple exist for the same opcode.

    Uses field default_value matching to disambiguate variants like
    costume number vs costume name.
    """
    if len(defs) == 1:
        return defs[0]

    block_fields = block.get("fields", {})

    for bd in defs:
        # Check if default_value fields match
        match = True
        for fs in bd.fields:
            if fs.default_value is not None:
                actual = block_fields.get(fs.name, [None])[0]
                if actual != fs.default_value:
                    match = False
                    break
        if match:
            return bd

    return defs[0]


def _reconstruct_pattern(blocks: dict, block: dict, block_def: Any) -> str:
    """Reconstruct the .scr text from a block using its BlockDef pattern."""
    pattern = block_def.pattern
    inputs = block.get("inputs", {})
    fields = block.get("fields", {})

    result_parts: list[str] = []
    i = 0

    while i < len(pattern):
        ch = pattern[i]

        if ch == "(":
            # Paren input: (NAME)
            end = pattern.index(")", i)
            name = pattern[i + 1:end]
            value = _decompile_input(blocks, inputs.get(name))
            result_parts.append(f"({value})")
            i = end + 1

        elif ch == "[":
            # Bracket: [NAME v] (field) or [NAME] (input)
            end = pattern.index("]", i)
            content = pattern[i + 1:end]

            if content.endswith(" v"):
                # Dropdown field: [NAME v]
                field_name = content[:-2].strip()
                # Try to get from fields first, then from menu shadow
                field_val = _get_field_or_menu_value(blocks, block, field_name, block_def)
                result_parts.append(f"[{field_val} v]")
            else:
                # String input: [NAME]
                name = content.strip()
                value = _decompile_input(blocks, inputs.get(name))
                result_parts.append(f"[{value}]")

            i = end + 1

        elif ch == "<":
            # Angle input: <NAME>
            end = pattern.index(">", i)
            name = pattern[i + 1:end]
            value = _decompile_boolean_input(blocks, inputs.get(name))
            result_parts.append(f"<{value}>")
            i = end + 1

        elif ch == " ":
            result_parts.append(" ")
            i += 1

        else:
            # Literal text — collect until next special char or space
            end = i
            while end < len(pattern) and pattern[end] not in "([< ":
                end += 1
            result_parts.append(pattern[i:end])
            i = end

    return "".join(result_parts)


# ---------------------------------------------------------------------------
# Input decompilation
# ---------------------------------------------------------------------------


def _decompile_input(blocks: dict, input_data: Any) -> str:
    """Decompile an input value to its text representation."""
    if input_data is None:
        return ""

    if not isinstance(input_data, list) or len(input_data) < 2:
        return str(input_data)

    shadow_type = input_data[0]  # 1=shadow, 2=no-shadow, 3=shadow+obscured
    value = input_data[1]

    # Value is a block ID (string) — nested reporter
    if isinstance(value, str) and value in blocks:
        reporter_block = blocks[value]
        opcode = reporter_block.get("opcode", "")

        # Skip menu shadow blocks — get their field value instead
        if reporter_block.get("shadow", False) and opcode not in _REPORTER_OPCODES:
            return _get_shadow_value(reporter_block)

        if opcode in _BOOLEAN_OPCODES:
            inner = _decompile_block_line(blocks, value)
            return f"<{inner}>"
        else:
            inner = _decompile_block_line(blocks, value)
            return f"({inner})"

    # Value is a primitive array [type_code, value_string]
    if isinstance(value, list) and len(value) >= 2:
        prim_type = value[0]
        prim_value = str(value[1])

        if prim_type == _PRIM_VARIABLE_TYPE:
            # [12, "var_name", "var_id"]
            return prim_value
        if prim_type == _PRIM_LIST_TYPE:
            # [13, "list_name", "list_id"]
            return prim_value
        if prim_type == _PRIM_BROADCAST_TYPE:
            # [11, "broadcast_name", "broadcast_id"]
            return prim_value
        if prim_type == _PRIM_COLOR_TYPE:
            return prim_value
        # Number or string literal
        return prim_value

    return str(value)


def _decompile_boolean_input(blocks: dict, input_data: Any) -> str:
    """Decompile a boolean input (angle bracket content)."""
    if input_data is None:
        return ""

    if not isinstance(input_data, list) or len(input_data) < 2:
        return ""

    value = input_data[1]

    if isinstance(value, str) and value in blocks:
        return _decompile_block_line(blocks, value)

    return ""


def _get_shadow_value(shadow_block: dict) -> str:
    """Get the display value from a shadow/menu block."""
    fields = shadow_block.get("fields", {})
    for field_name, field_data in fields.items():
        if isinstance(field_data, list) and len(field_data) >= 1:
            return str(field_data[0])
    return ""


def _get_field_or_menu_value(
    blocks: dict, block: dict, field_name: str, block_def: Any
) -> str:
    """Get a field value, checking direct fields, inputs, and menu shadows."""
    # Direct field
    fields = block.get("fields", {})
    if field_name in fields:
        return str(fields[field_name][0])

    # Check inputs — broadcast and other special inputs use [NAME v] pattern
    # but store the value as an input primitive
    inputs = block.get("inputs", {})
    if field_name in inputs:
        input_data = inputs[field_name]
        if isinstance(input_data, list) and len(input_data) >= 2:
            value = input_data[1]
            if isinstance(value, list) and len(value) >= 2:
                return str(value[1])

    # Menu shadow — check if there's a menu spec
    if block_def.menu and block_def.menu.field_name == field_name:
        input_name = block_def.menu.input_name
        input_data = inputs.get(input_name)
        if input_data and isinstance(input_data, list) and len(input_data) >= 2:
            shadow_id = input_data[1]
            if isinstance(shadow_id, str) and shadow_id in blocks:
                return _get_shadow_value(blocks[shadow_id])

    return field_name


# ---------------------------------------------------------------------------
# Procedure call decompilation
# ---------------------------------------------------------------------------


def _decompile_procedure_call(blocks: dict, block_id: str) -> str:
    """Decompile a procedures_call block."""
    block = blocks[block_id]
    mutation = block.get("mutation", {})
    proccode = mutation.get("proccode", "")
    arg_ids = json.loads(mutation.get("argumentids", "[]"))
    inputs = block.get("inputs", {})

    parts = proccode.split()
    result: list[str] = []
    arg_idx = 0

    for part in parts:
        if part == "%s":
            if arg_idx < len(arg_ids):
                arg_id = arg_ids[arg_idx]
                value = _decompile_input(blocks, inputs.get(arg_id))
                result.append(f"({value})")
            arg_idx += 1
        elif part == "%b":
            if arg_idx < len(arg_ids):
                arg_id = arg_ids[arg_idx]
                value = _decompile_boolean_input(blocks, inputs.get(arg_id))
                result.append(f"<{value}>")
            arg_idx += 1
        else:
            result.append(part)

    return " ".join(result)
