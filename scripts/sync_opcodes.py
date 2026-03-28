#!/usr/bin/env python3
"""Sync scrawl's block registry against scratch-vm's opcode definitions.

Fetches the canonical block files from scratchfoundation/scratch-vm on GitHub,
extracts all opcodes from getPrimitives(), getHats(), and getMonitored(),
then diffs against scrawl's registry_data.py to find missing blocks.

Usage:
    python scripts/sync_opcodes.py [--generate]

Options:
    --generate  Print skeleton BlockDef code for missing opcodes
"""

from __future__ import annotations

import json
import re
import sys
import urllib.request
from pathlib import Path

# scratch-vm block files on GitHub (raw content)
BASE_URL = "https://raw.githubusercontent.com/scratchfoundation/scratch-vm/develop/src/blocks"
BLOCK_FILES = [
    "scratch3_motion.js",
    "scratch3_looks.js",
    "scratch3_sound.js",
    "scratch3_event.js",
    "scratch3_control.js",
    "scratch3_sensing.js",
    "scratch3_operators.js",
    "scratch3_data.js",
    "scratch3_procedures.js",
]

# Legacy/internal opcodes that scrawl intentionally skips
SKIP_OPCODES = frozenset({
    # Legacy motion (Scratch 2.0 scrolling, not in Scratch 3.0 editor)
    "motion_scroll_right",
    "motion_scroll_up",
    "motion_align_scene",
    "motion_xscroll",
    "motion_yscroll",
    # Legacy looks
    "looks_hideallsprites",
    "looks_changestretchby",
    "looks_setstretchto",
    # Legacy control
    "control_get_counter",
    "control_incr_counter",
    "control_clear_counter",
    "control_all_at_once",
    # Non-standard (experimental, not in Scratch editor UI)
    "control_while",
    "control_for_each",
    # Legacy sensing
    "sensing_loud",
    "sensing_userid",
    # Implicit primitives (handled by codegen, not block definitions)
    "data_variable",
    "data_listcontents",
    # Argument reporters (handled by custom block system)
    "argument_reporter_string_number",
    "argument_reporter_boolean",
    # Menu shadow blocks (rendered inside parent blocks, not standalone)
    "sound_sounds_menu",
    "sound_beats_menu",
    "sound_effects_menu",
    "BROADCAST_OPTION",
})


def fetch_file(filename: str) -> str:
    url = f"{BASE_URL}/{filename}"
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            return resp.read().decode("utf-8")
    except Exception as e:
        print(f"  Warning: could not fetch {filename}: {e}", file=sys.stderr)
        return ""


def extract_opcodes(source: str) -> dict[str, str]:
    """Extract opcode -> type mapping from a scratch-vm block file.

    Returns dict like {"motion_movesteps": "primitive", "event_whenflagclicked": "hat"}.
    """
    opcodes: dict[str, str] = {}

    # Match opcodes in getPrimitives()
    in_primitives = False
    in_hats = False
    in_monitored = False

    for line in source.splitlines():
        stripped = line.strip()

        if "getPrimitives" in stripped:
            in_primitives = True
            in_hats = False
            in_monitored = False
        elif "getHats" in stripped:
            in_hats = True
            in_primitives = False
            in_monitored = False
        elif "getMonitored" in stripped:
            in_monitored = True
            in_primitives = False
            in_hats = False

        # Match opcode keys like: motion_movesteps: this.moveSteps
        m = re.match(r"(\w+_\w+)\s*:", stripped)
        if m:
            opcode = m.group(1)
            if in_primitives:
                opcodes[opcode] = "primitive"
            elif in_hats:
                opcodes.setdefault(opcode, "hat")
            elif in_monitored:
                opcodes.setdefault(opcode, "monitored")

    return opcodes


def get_scrawl_opcodes() -> set[str]:
    """Read all opcodes from scrawl's registry_data.py."""
    # Find registry_data.py relative to this script
    root = Path(__file__).resolve().parent.parent
    registry_path = root / "src" / "scrawl" / "compiler" / "registry_data.py"

    if not registry_path.exists():
        print(f"Error: {registry_path} not found", file=sys.stderr)
        sys.exit(1)

    source = registry_path.read_text()
    return set(re.findall(r'opcode="(\w+)"', source))


def category_from_opcode(opcode: str) -> str:
    return opcode.split("_", 1)[0]


def main():
    generate = "--generate" in sys.argv

    print("Fetching scratch-vm block definitions...")
    vm_opcodes: dict[str, str] = {}
    for filename in BLOCK_FILES:
        source = fetch_file(filename)
        if source:
            found = extract_opcodes(source)
            vm_opcodes.update(found)
            print(f"  {filename}: {len(found)} opcodes")

    print(f"\nTotal scratch-vm opcodes: {len(vm_opcodes)}")

    scrawl_opcodes = get_scrawl_opcodes()
    print(f"Total scrawl opcodes: {len(scrawl_opcodes)}")

    # Also count control_if_else which is handled by parser, not registry
    scrawl_opcodes.add("control_if_else")
    # procedures_definition and procedures_call are handled by custom block system
    scrawl_opcodes.add("procedures_definition")
    scrawl_opcodes.add("procedures_call")

    # Find missing
    missing = {
        op: typ
        for op, typ in vm_opcodes.items()
        if op not in scrawl_opcodes and op not in SKIP_OPCODES
    }

    if not missing:
        print("\nAll scratch-vm opcodes are covered! No gaps found.")
        return

    print(f"\nMissing opcodes ({len(missing)}):")
    by_category: dict[str, list[tuple[str, str]]] = {}
    for op, typ in sorted(missing.items()):
        cat = category_from_opcode(op)
        by_category.setdefault(cat, []).append((op, typ))

    for cat, ops in sorted(by_category.items()):
        print(f"\n  {cat}:")
        for op, typ in ops:
            print(f"    {op} ({typ})")

    if generate:
        print("\n# --- Skeleton BlockDef entries ---\n")
        for op, typ in sorted(missing.items()):
            shape = "BlockShape.STACK"
            has_next = ""
            if typ == "hat":
                shape = "BlockShape.HAT"
                has_next = "\n        has_next=True,"
            print(f"""    BlockDef(
        pattern="TODO",
        opcode="{op}",
        shape={shape},{has_next}
    ),""")


if __name__ == "__main__":
    main()
