"""Human-readable output formatting for CLI display."""

from __future__ import annotations

from typing import Any


def _has_rich() -> bool:
    try:
        import rich  # noqa: F401
        return True
    except ImportError:
        return False


def _truncate(s: str, max_len: int = 30) -> str:
    if len(s) <= max_len:
        return s
    return s[: max_len - 1] + "\u2026"


def _table(headers: list[str], rows: list[list[str]], min_widths: dict[int, int] | None = None) -> str:
    """Render a simple plain-text table."""
    if not rows:
        return "(no data)"

    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(widths):
                widths[i] = max(widths[i], len(cell))

    if min_widths:
        for i, w in min_widths.items():
            if i < len(widths):
                widths[i] = max(widths[i], w)

    def fmt_row(cells: list[str]) -> str:
        parts = []
        for i, cell in enumerate(cells):
            if i < len(widths):
                parts.append(cell.ljust(widths[i]))
            else:
                parts.append(cell)
        return "  ".join(parts)

    lines = [fmt_row(headers)]
    lines.append("  ".join("\u2500" * w for w in widths))
    for row in rows:
        lines.append(fmt_row(row))
    return "\n".join(lines)


def format_info(data: dict[str, Any]) -> str:
    lines = [
        "Project Summary",
        "\u2500" * 40,
        f"  Sprites:    {data['sprite_count']}",
        f"  Variables:  {data['variable_count']}",
        f"  Lists:      {data['list_count']}",
        f"  Blocks:     {data['block_count']}",
        f"  Costumes:   {data['costume_count']}",
        f"  Sounds:     {data['sound_count']}",
        f"  Monitors:   {data['monitor_count']}",
    ]
    if data["extensions"]:
        lines.append(f"  Extensions: {', '.join(data['extensions'])}")
    else:
        lines.append("  Extensions: (none)")

    meta = data.get("meta", {})
    if meta:
        lines.append("")
        lines.append("Metadata")
        lines.append("\u2500" * 40)
        for k, v in meta.items():
            val = _truncate(str(v), 60)
            lines.append(f"  {k}: {val}")

    return "\n".join(lines)


def format_sprites(data: list[dict[str, Any]]) -> str:
    headers = ["Name", "Type", "X", "Y", "Size", "Visible", "Costumes", "Blocks"]
    rows = []
    for s in data:
        stype = "Stage" if s["is_stage"] else "Sprite"
        x = str(round(s.get("x", 0))) if not s["is_stage"] else "-"
        y = str(round(s.get("y", 0))) if not s["is_stage"] else "-"
        size = str(round(s.get("size", 100))) if not s["is_stage"] else "-"
        visible = "\u2713" if s.get("visible", True) else "\u2717"
        rows.append(
            [
                _truncate(s["name"]),
                stype,
                x,
                y,
                size,
                visible if not s["is_stage"] else "-",
                str(s["costume_count"]),
                str(s["block_count"]),
            ]
        )
    return _table(headers, rows)


def format_variables(data: list[dict[str, Any]]) -> str:
    headers = ["Name", "Type", "Scope", "Value"]
    rows = []
    for v in data:
        if v["type"] == "variable":
            val = _truncate(str(v.get("value", "")), 40)
        else:
            val = f"[{v.get('length', 0)} items]"
        rows.append(
            [
                _truncate(v["name"]),
                v["type"],
                _truncate(v["scope"], 20),
                val,
            ]
        )
    return _table(headers, rows)


def format_blocks(data: dict[str, Any]) -> str:
    lines = [
        f"Total blocks: {data['total_blocks']}",
        f"Top-level stacks: {data['top_level_stacks']}",
        "",
        "By category:",
    ]

    headers = ["Category", "Count"]
    rows = [[cat, str(count)] for cat, count in data["by_category"].items()]
    lines.append(_table(headers, rows))

    if data.get("by_opcode"):
        lines.append("")
        lines.append("Top opcodes:")
        headers2 = ["Opcode", "Count"]
        top = list(data["by_opcode"].items())[:20]
        rows2 = [[op, str(c)] for op, c in top]
        lines.append(_table(headers2, rows2))

    return "\n".join(lines)


def format_assets(data: list[dict[str, Any]]) -> str:
    headers = ["MD5ext", "Name", "Type", "Format", "Target", "Size", "Exists"]
    rows = []
    for a in data:
        size = _format_size(a.get("file_size")) if a.get("file_size") is not None else "-"
        exists = "-"
        if a.get("file_exists") is True:
            exists = "\u2713"
        elif a.get("file_exists") is False:
            exists = "\u2717"
        rows.append(
            [
                _truncate(a["md5ext"], 40),
                _truncate(a["name"], 20),
                a["type"],
                a["data_format"],
                _truncate(a["target_name"], 15),
                size,
                exists,
            ]
        )
    return _table(headers, rows)


def format_tree(data: dict[str, Any]) -> str:
    lines = [f"\u250c {data['name']}"]

    if data["extensions"]:
        lines.append(f"\u2502  Extensions: {', '.join(data['extensions'])}")

    targets = data["targets"]
    for i, target in enumerate(targets):
        is_last = i == len(targets) - 1
        prefix = "\u2514" if is_last else "\u251c"
        cont = " " if is_last else "\u2502"

        label = "[Stage]" if target["is_stage"] else "[Sprite]"
        lines.append(f"{prefix}\u2500 {target['name']} {label}")

        items = []
        if target["costumes"]:
            names = ", ".join(c["name"] for c in target["costumes"][:5])
            extra = f" (+{len(target['costumes']) - 5} more)" if len(target["costumes"]) > 5 else ""
            items.append(f"Costumes ({len(target['costumes'])}): {names}{extra}")
        if target["sounds"]:
            names = ", ".join(s["name"] for s in target["sounds"][:5])
            items.append(f"Sounds ({len(target['sounds'])}): {names}")
        if target["variables"]:
            names = ", ".join(v["name"] for v in target["variables"][:5])
            extra = f" (+{len(target['variables']) - 5} more)" if len(target["variables"]) > 5 else ""
            items.append(f"Variables ({len(target['variables'])}): {names}{extra}")
        if target["lists"]:
            names = ", ".join(l["name"] for l in target["lists"][:5])
            items.append(f"Lists ({len(target['lists'])}): {names}")
        items.append(f"Blocks: {target['block_count']} ({target['top_level_stacks']} stacks)")

        for j, item in enumerate(items):
            is_last_item = j == len(items) - 1
            sub_prefix = "\u2514" if is_last_item else "\u251c"
            lines.append(f"{cont}  {sub_prefix}\u2500 {item}")

    return "\n".join(lines)


def format_validation(issues: list) -> str:
    if not issues:
        return "\u2713 Project is valid. No issues found."

    errors = [i for i in issues if i.severity == "error"]
    warnings = [i for i in issues if i.severity == "warning"]

    lines = []
    if errors:
        lines.append(f"\u2717 {len(errors)} error(s):")
        for e in errors:
            loc = f" [{e.target_name}]" if e.target_name else ""
            lines.append(f"  ERROR{loc}: {e.message}")

    if warnings:
        if lines:
            lines.append("")
        lines.append(f"! {len(warnings)} warning(s):")
        for w in warnings:
            loc = f" [{w.target_name}]" if w.target_name else ""
            lines.append(f"  WARN{loc}: {w.message}")

    lines.append("")
    lines.append(f"Total: {len(errors)} error(s), {len(warnings)} warning(s)")
    return "\n".join(lines)


def _format_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
