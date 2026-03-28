"""CLI entry point for the Scrawl tool."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path

from scrawl import io, inspect, modify, validate, formatting, generate
from scrawl.errors import ScrawlError


def main(argv: list[str] | None = None) -> int:
    """Main entry point. Returns exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if not hasattr(args, "func"):
        parser.print_help()
        return 1

    try:
        return args.func(args)
    except ScrawlError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scrawl",
        description="Scrawl — write Scratch 3.0 projects as text",
    )
    parser.add_argument(
        "--version", action="version", version="%(prog)s 0.1.0"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # --- Pack / Unpack ---
    p_unpack = subparsers.add_parser("unpack", help="Extract .sb3 to directory")
    p_unpack.add_argument("file", type=Path, help="Path to .sb3 file")
    p_unpack.add_argument(
        "--output", "-o", type=Path, default=None, help="Output directory"
    )
    p_unpack.set_defaults(func=cmd_unpack)

    p_pack = subparsers.add_parser("pack", help="Create .sb3 from directory")
    p_pack.add_argument("directory", type=Path, help="Directory containing project.json")
    p_pack.add_argument(
        "--output", "-o", type=Path, default=None, help="Output .sb3 file"
    )
    p_pack.set_defaults(func=cmd_pack)

    # --- Inspect commands ---
    for cmd_name, help_text, handler in [
        ("info", "Show project summary", cmd_info),
        ("sprites", "List all sprites", cmd_sprites),
        ("variables", "List all variables and lists", cmd_variables),
        ("blocks", "Show block statistics", cmd_blocks),
        ("assets", "List referenced assets", cmd_assets),
        ("tree", "Show project structure tree", cmd_tree),
    ]:
        p = subparsers.add_parser(cmd_name, help=help_text)
        p.add_argument(
            "project", type=Path, help="Path to .sb3 file or project directory"
        )
        p.add_argument("--json", action="store_true", help="Output as JSON")
        p.set_defaults(func=handler)

    # --- Modify commands ---
    p_rs = subparsers.add_parser("rename-sprite", help="Rename a sprite")
    p_rs.add_argument("project", type=Path, help="Path to .sb3 file or project directory")
    p_rs.add_argument("old_name", help="Current sprite name")
    p_rs.add_argument("new_name", help="New sprite name")
    p_rs.set_defaults(func=cmd_rename_sprite)

    p_rv = subparsers.add_parser("rename-variable", help="Rename a variable or list")
    p_rv.add_argument("project", type=Path, help="Path to .sb3 file or project directory")
    p_rv.add_argument("old_name", help="Current variable name")
    p_rv.add_argument("new_name", help="New variable name")
    p_rv.add_argument(
        "--sprite", default=None, help="Scope to a specific sprite (default: search all)"
    )
    p_rv.set_defaults(func=cmd_rename_variable)

    p_ds = subparsers.add_parser("delete-sprite", help="Delete a sprite and its assets")
    p_ds.add_argument("project", type=Path, help="Path to .sb3 file or project directory")
    p_ds.add_argument("sprite_name", help="Name of the sprite to delete")
    p_ds.set_defaults(func=cmd_delete_sprite)

    p_sm = subparsers.add_parser("set-meta", help="Edit metadata fields")
    p_sm.add_argument("project", type=Path, help="Path to .sb3 file or project directory")
    p_sm.add_argument("--key", required=True, help="Meta key (semver, vm, agent)")
    p_sm.add_argument("--value", required=True, help="New value")
    p_sm.set_defaults(func=cmd_set_meta)

    # --- Validate ---
    p_val = subparsers.add_parser("validate", help="Check project integrity")
    p_val.add_argument(
        "project", type=Path, help="Path to .sb3 file or project directory"
    )
    p_val.add_argument("--json", action="store_true", help="Output as JSON")
    p_val.set_defaults(func=cmd_validate)

    # --- Compile ---
    p_compile = subparsers.add_parser(
        "compile", help="Compile ScratchText script into project"
    )
    p_compile.add_argument("script", type=Path, help="Path to .scr file")
    p_compile.add_argument(
        "project", type=Path, help="Path to .sb3 file or project directory"
    )
    p_compile.add_argument(
        "--target", "-t", default=None,
        help="Target sprite name (default: Stage)",
    )
    p_compile.add_argument(
        "--dry-run", action="store_true",
        help="Print generated block JSON without modifying project",
    )
    p_compile.set_defaults(func=cmd_compile)

    # --- Init (project generator) ---
    p_init = subparsers.add_parser(
        "init", help="Create a new Scratch project from scratch"
    )
    p_init.add_argument("output", type=Path, help="Output directory or .sb3 file")
    p_init.add_argument(
        "--name", default="Project", help="Project name (default: Project)"
    )
    p_init.add_argument(
        "--sprite", action="append", default=[], metavar="NAME",
        help="Add a named sprite (can be repeated)",
    )
    p_init.add_argument(
        "--script", action="append", default=[], nargs=2,
        metavar=("TARGET", "FILE"),
        help="Compile a .scr file into TARGET (can be repeated)",
    )
    p_init.set_defaults(func=cmd_init)

    return parser


# ── Command handlers ──────────────────────────────────────────


def cmd_unpack(args: argparse.Namespace) -> int:
    output = args.output or args.file.with_suffix("")
    io.unpack_sb3(args.file, output)
    print(f"Unpacked to {output}")
    return 0


def cmd_pack(args: argparse.Namespace) -> int:
    output = args.output or args.directory.with_suffix(".sb3")
    io.pack_sb3(args.directory, output)
    print(f"Packed to {output}")
    return 0


def cmd_info(args: argparse.Namespace) -> int:
    project = io.load_project(args.project)
    data = inspect.get_project_info(project)
    if args.json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print(formatting.format_info(data))
    return 0


def cmd_sprites(args: argparse.Namespace) -> int:
    project = io.load_project(args.project)
    data = inspect.get_sprites(project)
    if args.json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print(formatting.format_sprites(data))
    return 0


def cmd_variables(args: argparse.Namespace) -> int:
    project = io.load_project(args.project)
    data = inspect.get_variables(project)
    if args.json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print(formatting.format_variables(data))
    return 0


def cmd_blocks(args: argparse.Namespace) -> int:
    project = io.load_project(args.project)
    data = inspect.get_block_stats(project)
    if args.json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print(formatting.format_blocks(data))
    return 0


def cmd_assets(args: argparse.Namespace) -> int:
    project = io.load_project(args.project)
    data = inspect.get_assets(project)
    if args.json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print(formatting.format_assets(data))
    return 0


def cmd_tree(args: argparse.Namespace) -> int:
    project = io.load_project(args.project)
    data = inspect.get_project_tree(project)
    if args.json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print(formatting.format_tree(data))
    return 0


def cmd_rename_sprite(args: argparse.Namespace) -> int:
    project, work_dir, needs_repack = io.load_project_for_modification(args.project)
    modify.rename_sprite(project, args.old_name, args.new_name)
    io.save_project_after_modification(project, work_dir, args.project, needs_repack)
    print(f"Renamed sprite '{args.old_name}' -> '{args.new_name}'")
    return 0


def cmd_rename_variable(args: argparse.Namespace) -> int:
    project, work_dir, needs_repack = io.load_project_for_modification(args.project)
    modify.rename_variable(project, args.old_name, args.new_name, args.sprite)
    io.save_project_after_modification(project, work_dir, args.project, needs_repack)
    print(f"Renamed variable '{args.old_name}' -> '{args.new_name}'")
    return 0


def cmd_delete_sprite(args: argparse.Namespace) -> int:
    project, work_dir, needs_repack = io.load_project_for_modification(args.project)
    deleted = modify.delete_sprite(project, args.sprite_name)
    io.save_project_after_modification(project, work_dir, args.project, needs_repack)
    print(f"Deleted sprite '{args.sprite_name}'")
    if deleted:
        print(f"Removed {len(deleted)} exclusive asset(s): {', '.join(deleted)}")
    return 0


def cmd_set_meta(args: argparse.Namespace) -> int:
    project, work_dir, needs_repack = io.load_project_for_modification(args.project)
    modify.set_meta(project, args.key, args.value)
    io.save_project_after_modification(project, work_dir, args.project, needs_repack)
    print(f"Set meta.{args.key} = '{args.value}'")
    return 0


def cmd_compile(args: argparse.Namespace) -> int:
    from scrawl.compiler import compile_script

    script_text = args.script.read_text(encoding="utf-8")

    if args.dry_run:
        # Load without modification flow
        project = io.load_project(args.project)
        target_name = args.target or "Stage"
        target = project.get_target_by_name(target_name)
        if target is None:
            print(f"Error: Target '{target_name}' not found", file=sys.stderr)
            return 1
        blocks = compile_script(script_text, target, project)
        print(json.dumps(blocks, indent=2, ensure_ascii=False))
        return 0

    project, work_dir, needs_repack = io.load_project_for_modification(args.project)
    target_name = args.target or "Stage"
    target = project.get_target_by_name(target_name)
    if target is None:
        print(f"Error: Target '{target_name}' not found", file=sys.stderr)
        return 1

    blocks = compile_script(script_text, target, project)
    io.save_project_after_modification(project, work_dir, args.project, needs_repack)
    print(f"Compiled {len(blocks)} blocks into '{target_name}'")

    # Post-compile validation
    issues = validate.validate_project(project)
    errors = [i for i in issues if i.severity == "error"]
    if errors:
        print(f"Warning: {len(errors)} validation error(s) after compilation:", file=sys.stderr)
        for e in errors[:5]:
            print(f"  {e.message}", file=sys.stderr)
    return 0


def cmd_init(args: argparse.Namespace) -> int:
    from scrawl.compiler import compile_script
    from scrawl.model import ScratchProject

    # 1. Create base project
    project_data, asset_files = generate.create_project(name=args.name)

    # 2. Add requested sprites
    for sprite_name in args.sprite:
        sprite_assets = generate.add_sprite(project_data, sprite_name)
        asset_files.update(sprite_assets)

    # 3. Determine output: directory or .sb3
    output = Path(args.output)
    is_sb3 = output.suffix == ".sb3"
    if is_sb3:
        work_dir = Path(tempfile.mkdtemp(prefix="sb3_init_"))
    else:
        work_dir = output

    # 4. Write project files to work_dir
    generate.write_project(project_data, asset_files, work_dir)

    # 5. Compile scripts if any
    if args.script:
        project = ScratchProject(project_data, base_path=work_dir)
        for target_name, script_path in args.script:
            target = project.get_target_by_name(target_name)
            if target is None:
                print(f"Error: Target '{target_name}' not found", file=sys.stderr)
                if is_sb3:
                    shutil.rmtree(work_dir, ignore_errors=True)
                return 1
            source = Path(script_path).read_text(encoding="utf-8")
            blocks = compile_script(source, target, project)
            print(f"  Compiled {len(blocks)} blocks into '{target_name}'")
        # Re-save after compilation
        project.save(work_dir / "project.json")

    # 6. Validate
    project = ScratchProject(project_data, base_path=work_dir)
    issues = validate.validate_project(project)
    errors = [i for i in issues if i.severity == "error"]

    # 7. Pack to .sb3 if needed
    if is_sb3:
        io.pack_sb3(work_dir, output)
        shutil.rmtree(work_dir, ignore_errors=True)

    # 8. Report
    print(f"Created project at {output}")
    if args.sprite:
        print(f"  Sprites: {', '.join(args.sprite)}")
    if errors:
        print(f"Warning: {len(errors)} validation error(s):", file=sys.stderr)
        for e in errors[:5]:
            print(f"  {e.message}", file=sys.stderr)

    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    project = io.load_project(args.project)
    issues = validate.validate_project(project)
    if args.json:
        print(
            json.dumps(
                [
                    {
                        "severity": i.severity,
                        "category": i.category,
                        "message": i.message,
                        "target_name": i.target_name,
                        "block_id": i.block_id,
                    }
                    for i in issues
                ],
                indent=2,
                ensure_ascii=False,
            )
        )
    else:
        print(formatting.format_validation(issues))
    errors = [i for i in issues if i.severity == "error"]
    return 1 if errors else 0
