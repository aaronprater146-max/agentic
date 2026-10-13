"""Command-line interface for creating and building UE 5.8.3 plugins with Antigravity."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

from .antigravity import init_antigravity_workspace
from .builder import PluginBuilder
from .creator import PluginScaffolder
from .engine_locator import find_engine
from .validator import PluginValidator


def discover_plugins(search_root: Optional[Path] = None) -> list[Path]:
    root = search_root or Path.cwd()
    found: list[Path] = []
    # Search root, direct children, Plugins/
    for p in root.glob("*.uplugin"):
        found.append(p.parent)
    for p in root.glob("*/*.uplugin"):
        found.append(p.parent)
    for p in root.glob("Plugins/*/*.uplugin"):
        found.append(p.parent)

    # Return unique sorted directories
    seen = set()
    result = []
    for d in found:
        res = d.resolve()
        if res not in seen and not any(part.startswith(".") for part in res.parts):
            seen.add(res)
            result.append(res)
    return sorted(result, key=lambda x: x.name)


def cmd_create(args: argparse.Namespace) -> int:
    print(f"==> Creating Unreal Engine {args.engine_version} plugin: '{args.name}'...")
    scaffolder = PluginScaffolder(engine_version=args.engine_version)
    try:
        plugin_dir = scaffolder.create(
            name=args.name,
            template=args.template,
            output_dir=args.output_dir,
            author=args.author,
            description=args.description,
            category=args.category,
            with_antigravity=True,
        )
        print(f"==> Successfully generated plugin at: {plugin_dir}")
        print(f"    Template: {args.template}")
        print(f"    Manifest: {plugin_dir}/{plugin_dir.name}.uplugin")
        print(f"\nNext steps:")
        print(f"  * Build it with Antigravity: agentic build {plugin_dir.name}")
        print(f"  * Package for release:       agentic package {plugin_dir.name}")
        return 0
    except Exception as e:
        print(f"Error creating plugin: {e}", file=sys.stderr)
        return 1


def cmd_build(args: argparse.Namespace) -> int:
    builder = PluginBuilder(engine_path=args.engine_path)

    # If no plugin specified, find first available plugin
    target = args.plugin
    if not target:
        plugins = discover_plugins()
        if not plugins:
            print("Error: No plugins found to build. Specify a plugin name or path.", file=sys.stderr)
            return 1
        target = plugins[0]
        print(f"No plugin specified; auto-selected '{target.name}'.")

    print(f"==> Building plugin '{target}' (Mode: {args.mode.upper()})...")
    if args.mode == "uat":
        res = builder.package_uat(
            plugin_target=target,
            target_platforms=[args.platform] if args.platform else None,
            dry_run=args.dry_run,
        )
    else:
        res = builder.build_ubt(
            plugin_target=target,
            target_platform=args.platform,
            configuration=args.configuration,
            dry_run=args.dry_run,
        )

    if res.log_tail:
        print(res.log_tail)

    if res.success:
        print(f"==> Build SUCCEEDED for '{res.plugin_name}'.")
        return 0
    else:
        print(f"==> Build FAILED for '{res.plugin_name}' (exit code: {res.exit_code}).", file=sys.stderr)
        return res.exit_code or 1


def cmd_package(args: argparse.Namespace) -> int:
    builder = PluginBuilder(engine_path=args.engine_path)
    target = args.plugin
    if not target:
        plugins = discover_plugins()
        if not plugins:
            print("Error: No plugins found to package. Specify a plugin name or path.", file=sys.stderr)
            return 1
        target = plugins[0]

    print(f"==> Packaging plugin '{target}' with RunUAT...")
    res = builder.package_uat(
        plugin_target=target,
        output_dir=args.output_dir,
        target_platforms=[args.platform] if args.platform else None,
        dry_run=args.dry_run,
    )

    if res.log_tail:
        print(res.log_tail)

    if res.success:
        print(f"==> Package SUCCEEDED for '{res.plugin_name}' -> {res.output_path}")
        return 0
    else:
        print(f"==> Package FAILED for '{res.plugin_name}' (exit code: {res.exit_code}).", file=sys.stderr)
        return res.exit_code or 1


def cmd_validate(args: argparse.Namespace) -> int:
    validator = PluginValidator(target_engine_version=args.engine_version)

    targets: list[Path] = []
    if args.all or not args.plugin:
        targets = discover_plugins()
        if not targets and args.plugin:
            targets = [Path(args.plugin)]
    else:
        targets = [Path(args.plugin)]

    if not targets:
        print("No plugins found to validate.", file=sys.stderr)
        return 1

    total_errors = 0
    total_warnings = 0

    print(f"==> Validating {len(targets)} plugin(s) for Unreal Engine {args.engine_version}...")
    for t in targets:
        report = validator.validate_plugin(t)
        status = "PASSED" if report.is_valid else "FAILED"
        print(f"\n--- [{status}] {report.plugin_name} ({report.plugin_path}) ---")
        for err in report.errors:
            print(f"  [ERROR]   {err.file.name}: {err.message}")
            total_errors += 1
        for warn in report.warnings:
            print(f"  [WARNING] {warn.file.name}: {warn.message}")
            total_warnings += 1
        if not report.issues:
            print("  All schema, C++20, and module layout checks passed cleanly.")

    print(f"\nSummary: {len(targets)} plugins checked, {total_errors} error(s), {total_warnings} warning(s).")
    return 0 if total_errors == 0 else 1


def cmd_list(args: argparse.Namespace) -> int:
    plugins = discover_plugins()
    if not plugins:
        print("No Unreal Engine plugins found in the workspace.")
        return 0

    print(f"Found {len(plugins)} Unreal Engine plugin(s):")
    for p in plugins:
        uplugin_files = list(p.glob("*.uplugin"))
        manifest = uplugin_files[0].name if uplugin_files else "(no .uplugin)"
        print(f"  * {p.name:<30} [{manifest}] at {p}")
    return 0


def cmd_init_antigravity(args: argparse.Namespace) -> int:
    target = args.path or "."
    print(f"==> Initializing Antigravity IDE configuration in: {target}")
    files = init_antigravity_workspace(target)
    for f in files:
        print(f"  Created: {f}")
    print("\nAntigravity tasks and workspace configured!")
    print("Press Ctrl+Shift+B in Antigravity to run 'UE5: Build Plugin'.")
    return 0


def cmd_info(args: argparse.Namespace) -> int:
    engine_path = getattr(args, "engine_path", None)
    engine = find_engine(engine_path)
    print("=== Agentic Unreal Engine 5.8 Environment ===")
    if engine and engine.is_valid:
        print(f"Engine Detected:      {engine}")
        print(f"Version:              {engine.version_str} (UE 5.8: {'Yes' if engine.is_ue58 else 'No'})")
        print(f"UBT Batch Tool:       {engine.ubt_path or 'Not found'}")
        print(f"UAT Automation Tool:  {engine.uat_path or 'Not found'}")
        print(f"Editor Executable:    {engine.editor_path or 'Not found'}")
    else:
        print("Engine Detected:      None in standard paths.")
        print("Tip: Set UNREAL_INSTALL_DIR or pass --engine-path to specify engine location.")
        print("Note: Agentic supports full dry-run compilation and validation without an engine.")

    plugins = discover_plugins()
    print(f"\nPlugins in workspace: {len(plugins)}")
    for p in plugins:
        print(f"  - {p.name}")
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="agentic",
        description="Create and build Unreal Engine 5.8.3 plugins easily with Antigravity IDE.",
    )
    subparsers = parser.add_subparsers(dest="subcommand", help="Available commands")

    # create
    p_create = subparsers.add_parser("create", help="Scaffold a new UE 5.8.3 plugin")
    p_create.add_argument("name", help="Name of the plugin to create")
    p_create.add_argument(
        "-t",
        "--template",
        default="runtime",
        choices=["runtime", "editor", "blueprint-library", "agent", "minimal"],
        help="Plugin template architecture (default: runtime)",
    )
    p_create.add_argument("-e", "--engine-version", default="5.8.3", help="Target engine version (default: 5.8.3)")
    p_create.add_argument("-o", "--output-dir", default=None, help="Output directory (default: ./Plugins/<Name>)")
    p_create.add_argument("-a", "--author", default="Agentic Developer", help="Plugin author")
    p_create.add_argument("-d", "--description", default=None, help="Plugin description")
    p_create.add_argument("-c", "--category", default=None, help="Plugin category")
    p_create.set_defaults(func=cmd_create)

    # build
    p_build = subparsers.add_parser("build", help="Build a plugin via scratch UBT or RunUAT")
    p_build.add_argument("plugin", nargs="?", default=None, help="Plugin directory or name (default: auto-detect)")
    p_build.add_argument("-e", "--engine-path", default=None, help="Explicit path to Unreal Engine root")
    p_build.add_argument("-m", "--mode", choices=["ubt", "uat"], default="ubt", help="Build mode (default: ubt)")
    p_build.add_argument("-p", "--platform", default=None, help="Target platform (Linux, Win64, Mac)")
    p_build.add_argument(
        "-c",
        "--configuration",
        default="Development",
        choices=["Development", "DebugGame", "Shipping"],
        help="Build configuration (default: Development)",
    )
    p_build.add_argument("--dry-run", action="store_true", help="Generate project & display commands without compiling")
    p_build.set_defaults(func=cmd_build)

    # package
    p_package = subparsers.add_parser("package", help="Package a plugin for distribution with RunUAT")
    p_package.add_argument("plugin", nargs="?", default=None, help="Plugin directory or name")
    p_package.add_argument("-e", "--engine-path", default=None, help="Explicit path to Unreal Engine root")
    p_package.add_argument("-o", "--output-dir", default=None, help="Output directory for packaged plugin")
    p_package.add_argument("-p", "--platform", default=None, help="Target platform (Win64, Linux, Mac)")
    p_package.add_argument("--dry-run", action="store_true", help="Display packaging commands without running")
    p_package.set_defaults(func=cmd_package)

    # validate
    p_val = subparsers.add_parser("validate", help="Lint and validate plugin schema, C++20, and module structure")
    p_val.add_argument("plugin", nargs="?", default=None, help="Plugin to validate")
    p_val.add_argument("--all", action="store_true", help="Validate all plugins in the workspace")
    p_val.add_argument("-e", "--engine-version", default="5.8.3", help="Expected engine version (default: 5.8.3)")
    p_val.set_defaults(func=cmd_validate)

    # list
    p_list = subparsers.add_parser("list", help="List all plugins found in workspace")
    p_list.set_defaults(func=cmd_list)

    # init-antigravity
    p_init = subparsers.add_parser("init-antigravity", help="Set up Antigravity tasks & workspace configs")
    p_init.add_argument("path", nargs="?", default=".", help="Directory to configure (default: current directory)")
    p_init.set_defaults(func=cmd_init_antigravity)

    # info
    p_info = subparsers.add_parser("info", help="Display environment, engine paths, and detected plugins")
    p_info.add_argument("-e", "--engine-path", default=None, help="Explicit path to Unreal Engine root")
    p_info.set_defaults(func=cmd_info)

    parsed = parser.parse_args(argv)
    if not parsed.subcommand:
        parser.print_help()
        return 0

    return parsed.func(parsed)


if __name__ == "__main__":
    sys.exit(main())
