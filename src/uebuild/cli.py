"""``uebuild`` command line interface.

Subcommands::

    uebuild engines list|add|remove|show     manage known UE4/UE5 installs
    uebuild plugin info <x.uplugin>          inspect a plugin descriptor
    uebuild build --plugin X.uplugin ...     one headless BuildPlugin run
    uebuild matrix --config matrix.json      many engines/platforms from a file
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence

from . import __version__, matrix, report, util
from .build import BuildRequest, BuildResult, run_build
from .engine import (
    DEFAULT_PLATFORMS,
    EngineRegistry,
    all_engines,
    discover_engines,
    infer_engine_for_plugin,
    resolve_engine,
)
from .errors import UEBuildError
from .plugin import PluginDescriptor
from .util import colorize

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_BUILD_FAILED = 2


class _Ui:
    def __init__(self, use_color: bool):
        self.use_color = use_color

    def c(self, text: str, *styles: str) -> str:
        return colorize(text, *styles, enabled=self.use_color)

    def info(self, msg: str) -> None:
        print("%s %s" % (self.c("uebuild:", "cyan", "bold"), msg))

    def warn(self, msg: str) -> None:
        print("%s %s" % (self.c("warning:", "yellow", "bold"), msg), file=sys.stderr)

    def error(self, msg: str) -> None:
        print("%s %s" % (self.c("error:", "red", "bold"), msg), file=sys.stderr)

    def success(self, msg: str) -> None:
        print("%s %s" % (self.c("ok:", "green", "bold"), msg))


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="uebuild",
        description="Headless UE4/UE5 plugin builder powered by RunUAT BuildPlugin.",
    )
    parser.add_argument("--version", action="version", version="uebuild %s" % __version__)
    sub = parser.add_subparsers(dest="command", metavar="<command>")
    sub.required = True

    # ---- engines -------------------------------------------------------
    engines = sub.add_parser("engines", help="manage known engine installs")
    engines_sub = engines.add_subparsers(dest="engines_command", metavar="<action>")
    engines_sub.required = True

    engines_list = engines_sub.add_parser("list", help="list known installs")
    engines_list.add_argument(
        "--no-discover",
        action="store_true",
        help="only show manually registered engines (skip disk scan)",
    )
    engines_list.add_argument("--json", action="store_true", help="machine output")

    engines_add = engines_sub.add_parser("add", help="register an engine root")
    engines_add.add_argument("path", nargs="?", help="path to UE_4.x / UE_5.x root")
    engines_add.add_argument(
        "--discover",
        action="store_true",
        help="register every install found on this machine instead of one path",
    )
    engines_add.add_argument("--name", help="registry name override")

    engines_remove = engines_sub.add_parser("remove", help="unregister an engine")
    engines_remove.add_argument("query", help="registry name or root path")

    engines_show = engines_sub.add_parser("show", help="details for one install")
    engines_show.add_argument("query", help="name, version or path")
    engines_show.add_argument("--json", action="store_true")

    # ---- plugin --------------------------------------------------------
    plugin = sub.add_parser("plugin", help="inspect a .uplugin descriptor")
    plugin_sub = plugin.add_subparsers(dest="plugin_command", metavar="<action>")
    plugin_sub.required = True
    plugin_info = plugin_sub.add_parser("info", help="show descriptor details")
    plugin_info.add_argument("plugin", help="path to .uplugin or its folder")
    plugin_info.add_argument("--engine", help="also check compatibility with this engine")
    plugin_info.add_argument("--json", action="store_true")

    # ---- build ---------------------------------------------------------
    build = sub.add_parser("build", help="run one BuildPlugin job")
    build.add_argument("--plugin", required=True, help="path to .uplugin or its folder")
    build.add_argument(
        "--engine",
        help="engine selector: version (5.3, 4.27), registry name, path, "
        "'latest', 'latest-ue4', 'latest-ue5'. Default: best match from "
        "the plugin's EngineVersion",
    )
    build.add_argument(
        "--platforms",
        help="'+' or ',' separated target platforms "
        "(default: %s)" % "+".join(DEFAULT_PLATFORMS),
    )
    build.add_argument("--output", help="package output dir (default: dist/<plugin>/<engine>)")
    build.add_argument("--rocket", action="store_true",
                       help="build a Rocket (binary distribution) package for Fab/Marketplace")
    build.add_argument("--create-subfolder", action="store_true",
                       help="put output in an extra <PluginName> subfolder")
    build.add_argument("--no-debug-info", action="store_true",
                       help="strip debug information from binaries")
    build.add_argument("--strict-includes", action="store_true",
                       help="fail on missing include directives (UE4.26+/UE5)")
    build.add_argument("--no-host-platform", action="store_true",
                       help="do not build for the host editor platform")
    build.add_argument(
        "--uat-arg",
        action="append",
        default=[],
        metavar="KEY[=VALUE]",
        help="extra BuildPlugin argument(s), repeatable; 'KEY' becomes -KEY, "
        "'KEY=VALUE' becomes -KEY=VALUE",
    )
    build.add_argument("--timeout", type=int, default=None,
                       help="kill the build after N seconds (default 4h)")
    build.add_argument("--no-timeout", action="store_true", help="never time out")
    build.add_argument("--logs-dir", help="where to write build logs")
    build.add_argument("--quiet", action="store_true", help="do not stream UAT output")
    build.add_argument("--dry-run", action="store_true",
                       help="print the RunUAT command without executing it")
    build.add_argument("--report-json", metavar="PATH", help="write a JSON report")
    build.add_argument("--report-html", metavar="PATH", help="write an HTML report")

    # ---- matrix --------------------------------------------------------
    mtx = sub.add_parser("matrix", help="build many engine/platform combos from a config")
    mtx.add_argument("--config", required=True, help="path to matrix JSON config")
    mtx.add_argument("--quiet", action="store_true")
    mtx.add_argument("--dry-run", action="store_true",
                     help="print what would run without executing")
    mtx.add_argument("--stop-on-fail", action="store_true",
                     help="abort the matrix at the first failed build")
    mtx.add_argument("--report-json", metavar="PATH")
    mtx.add_argument("--report-html", metavar="PATH")
    mtx.add_argument("--title", default="uebuild plugin build report",
                     help="HTML report title")
    return parser


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_platforms(raw: Optional[str], engine) -> List[str]:
    if not raw:
        return [p for p in DEFAULT_PLATFORMS if p in engine.supported_platforms] or list(
            DEFAULT_PLATFORMS
        )
    parts = raw.replace(",", "+").split("+")
    return [p.strip() for p in parts if p.strip()]


def _parse_uat_args(items: Sequence[str], ui: _Ui) -> Dict[str, object]:
    result: Dict[str, object] = {}
    for item in items:
        key, sep, value = item.partition("=")
        key = key.strip().lstrip("-")
        if not key:
            ui.warn("ignoring empty --uat-arg %r" % item)
            continue
        result[key] = value if sep else True
    return result


def _pick_engine(args_engine: Optional[str], descriptor: PluginDescriptor,
                 registry: EngineRegistry, ui: _Ui):
    known = all_engines(registry)
    if args_engine:
        return resolve_engine(args_engine, engines=known)
    engine = infer_engine_for_plugin(descriptor.engine_version, known)
    if engine is None:
        raise UEBuildError(
            "no engine installs found; use 'uebuild engines add <UE_5.x path>'"
        )
    ui.info(
        "no --engine given; picked %s (plugin EngineVersion=%s)"
        % (engine.display, descriptor.engine_version or "not set")
    )
    return engine


def _print_result_line(ui: _Ui, result: BuildResult) -> None:
    status = ui.c("PASS", "green", "bold") if result.success else ui.c("FAIL", "red", "bold")
    print(
        "[%s] %s  (%s, e:%d w:%d)"
        % (
            status,
            result.label,
            util.human_duration(result.duration_s),
            result.error_count,
            result.warning_count,
        )
    )
    if not result.success and result.message:
        print("      %s" % ui.c(result.message, "red"))


def _write_reports(
    results: Sequence[BuildResult],
    json_path: Optional[str],
    html_path: Optional[str],
    ui: _Ui,
    html_title: str = "uebuild plugin build report",
) -> None:
    if json_path:
        ui.info("JSON report: %s" % report.write_json(results, json_path))
    if html_path:
        ui.info("HTML report: %s" % report.write_html(results, html_path, title=html_title))


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------

def cmd_engines_list(args, ui: _Ui) -> int:
    registry = EngineRegistry()
    installs = registry.entries() if args.no_discover else all_engines(registry)
    if args.json:
        print(json.dumps([e.describe() for e in installs], indent=2))
        return EXIT_OK
    if not installs:
        ui.warn("no engine installs found; add one with 'uebuild engines add <path>'")
        return EXIT_OK
    for install in installs:
        marker = " " if install.uat_script.is_file() else ui.c("!", "red", "bold")
        source = ui.c("registered", "cyan") if install.custom else "discovered"
        print("%s %-16s %-6s %-24s %s" % (
            marker,
            install.name,
            install.family_label + " " + install.version_str,
            source,
            install.root,
        ))
    return EXIT_OK


def cmd_engines_add(args, ui: _Ui) -> int:
    registry = EngineRegistry()
    if args.discover:
        found = discover_engines()
        if not found:
            ui.warn("discover found nothing on this machine")
            return EXIT_OK
        for install in found:
            added = registry.add(install.root)
            ui.success("registered %s" % added.display)
        return EXIT_OK
    if not args.path:
        raise UEBuildError("engines add needs a path (or --discover)")
    install = registry.add(args.path, name=args.name)
    ui.success("registered %s" % install.display)
    return EXIT_OK


def cmd_engines_remove(args, ui: _Ui) -> int:
    registry = EngineRegistry()
    if registry.remove(args.query):
        ui.success("removed '%s' from %s" % (args.query, registry.path))
    else:
        ui.warn("no registered engine matches '%s'" % args.query)
    return EXIT_OK


def cmd_engines_show(args, ui: _Ui) -> int:
    install = resolve_engine(args.query)
    if args.json:
        print(json.dumps(install.describe(), indent=2))
        return EXIT_OK
    details = install.describe()
    for key in ("name", "family", "version", "root", "uat", "uatExists",
                "branch", "licenseeVersion", "registered"):
        print("%-16s %s" % (key + ":", details[key]))
    print("%-16s %s" % ("platforms:", "+".join(details["platforms"])))
    return EXIT_OK


def cmd_plugin_info(args, ui: _Ui) -> int:
    descriptor = PluginDescriptor.from_file(args.plugin)
    warnings = descriptor.validate()
    engine_obj = None
    if args.engine:
        engine_obj = resolve_engine(args.engine)
        warnings = descriptor.validate(engine=engine_obj)
    if args.json:
        payload = descriptor.describe()
        payload["warnings"] = warnings
        print(json.dumps(payload, indent=2))
        return EXIT_OK
    fields = [
        ("name", descriptor.name),
        ("friendly name", descriptor.friendly_name),
        ("version", descriptor.semantic_version or "-"),
        ("engine version", descriptor.engine_version or "-"),
        ("descriptor format", descriptor.file_version),
        ("content only", "yes" if descriptor.content_only else "no"),
        ("can contain content", "yes" if descriptor.can_contain_content else "no"),
        ("supported platforms",
         "+".join(descriptor.supported_target_platforms) or "(all)"),
    ]
    for label, value in fields:
        print("%-20s %s" % (label + ":", value))
    if descriptor.modules:
        print("modules:")
        for module in descriptor.modules:
            print("  - %s (%s, %s)" % (module.name, module.module_type, module.loading_phase))
    for warning in warnings:
        ui.warn(warning)
    return EXIT_OK


def cmd_build(args, ui: _Ui) -> int:
    registry = EngineRegistry()
    descriptor = PluginDescriptor.from_file(args.plugin)
    engine = _pick_engine(args.engine, descriptor, registry, ui)
    platforms = _parse_platforms(args.platforms, engine)

    if args.output:
        output = Path(args.output)
    else:
        output = Path.cwd() / "dist" / descriptor.name / engine.version_str

    timeout_kwargs = {}
    if args.no_timeout:
        timeout_kwargs["timeout"] = None          # disable the 4h safeguard
    elif args.timeout:
        timeout_kwargs["timeout"] = float(args.timeout)

    request = BuildRequest(
        plugin=descriptor.path,
        engine=engine,
        output=output,
        platforms=platforms,
        rocket=args.rocket,
        create_subfolder=args.create_subfolder,
        no_debug_info=args.no_debug_info,
        strict_includes=args.strict_includes,
        no_host_platform=args.no_host_platform,
        extra_uat_args=_parse_uat_args(args.uat_arg, ui),
        logs_dir=Path(args.logs_dir) if args.logs_dir else None,
        **timeout_kwargs,
    )

    fatal, notes = request.validate()
    for note in notes:
        ui.warn(note)
    if fatal:
        for problem in fatal:
            ui.error(problem)
        return EXIT_ERROR

    if args.dry_run:
        ui.info("dry run: would execute")
        print("  %s" % request.command_string())
        print("  package: %s" % request.output_abs())
        return EXIT_OK

    result = run_build(request, echo=not args.quiet)
    print()
    _print_result_line(ui, result)
    if result.log_file:
        print("      log: %s" % result.log_file)
    if result.success and result.packaged_uplugin:
        ui.success("packaged: %s" % result.packaged_uplugin)
    elif not result.success and result.packaged_uplugin:
        ui.warn("partial output left behind: %s" % result.package_dir)

    _write_reports([result], args.report_json, args.report_html, ui)
    return EXIT_OK if result.success else EXIT_BUILD_FAILED


def cmd_matrix(args, ui: _Ui) -> int:
    config = matrix.load_matrix(args.config)
    requests = matrix.expand_matrix(config)
    ui.info("matrix expands to %d build(s)" % len(requests))

    if args.dry_run:
        for idx, request in enumerate(requests, 1):
            print("== %d/%d %s" % (idx, len(requests), request.default_label()))
            print("   %s" % request.command_string())
        return EXIT_OK

    results: List[BuildResult] = []
    for idx, request in enumerate(requests, 1):
        print()
        print(ui.c("== [%d/%d] %s" % (idx, len(requests), request.default_label()), "bold"))
        fatal, notes = request.validate()
        for note in notes:
            ui.warn(note)
        if fatal:
            result = run_build(request, echo=False)  # returns a failed result
        else:
            result = run_build(request, echo=not args.quiet)
        results.append(result)
        _print_result_line(ui, result)
        if not result.success and args.stop_on_fail:
            ui.error("stopping matrix early (--stop-on-fail)")
            break

    print()
    passed = sum(1 for r in results if r.success)
    ui.info("matrix finished: %d/%d passed" % (passed, len(results)))
    for result in results:
        _print_result_line(ui, result)

    _write_reports(results, args.report_json, args.report_html, ui,
                   html_title=args.title)
    return EXIT_OK if passed == len(results) else EXIT_BUILD_FAILED


# ---------------------------------------------------------------------------

_COMMAND_HANDLERS = {
    ("engines", "list"): cmd_engines_list,
    ("engines", "add"): cmd_engines_add,
    ("engines", "remove"): cmd_engines_remove,
    ("engines", "show"): cmd_engines_show,
    ("plugin", "info"): cmd_plugin_info,
}


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = make_parser()
    args = parser.parse_args(argv)
    ui = _Ui(use_color=util.supports_color(sys.stderr))
    try:
        if args.command == "build":
            return cmd_build(args, ui)
        if args.command == "matrix":
            return cmd_matrix(args, ui)
        handler = _COMMAND_HANDLERS.get((args.command, getattr(args, "%s_command" % args.command)))
        if handler is None:
            parser.error("unknown command")
            return EXIT_ERROR
        return handler(args, ui)
    except UEBuildError as exc:
        ui.error(str(exc))
        return EXIT_ERROR
    except KeyboardInterrupt:
        ui.error("interrupted")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
