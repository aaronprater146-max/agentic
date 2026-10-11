"""Build-matrix config files: build one plugin against many engines/platforms.

Example ``matrix.json``::

    {
      "defaults": {
        "platforms": ["Win64", "Linux"],
        "outputRoot": "dist",
        "rocket": true,
        "strictIncludes": true,
        "extraUatArgs": {"Unversioned": true}
      },
      "jobs": [
        {
          "plugin": "Plugins/Foo/Foo.uplugin",
          "engines": ["4.27", "5.3"]
        },
        {
          "plugin": "Plugins/Bar/Bar.uplugin",
          "engines": [{"name": "latest-ue5", "platforms": ["Win64"]}]
        }
      ]
    }
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Sequence

from .build import BuildRequest
from .engine import (
    DEFAULT_PLATFORMS,
    EngineInstall,
    EngineRegistry,
    all_engines,
    resolve_engine,
)
from .errors import ConfigError, PluginError
from .plugin import PluginDescriptor

_TOP_LEVEL_KEYS = {"defaults", "jobs"}


def _strip_json_comments(text: str) -> str:
    """Tolerate ``//`` full-line comments in hand-written config files."""
    kept = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("//"):
            continue
        kept.append(line)
    return "\n".join(kept)


def load_matrix(path) -> Dict[str, object]:
    path = Path(path).expanduser()
    if not path.is_file():
        raise ConfigError("matrix config not found: %s" % path)
    try:
        data = json.loads(_strip_json_comments(path.read_text(encoding="utf-8-sig")))
    except ValueError as exc:
        raise ConfigError("%s is not valid JSON: %s" % (path, exc)) from exc
    if not isinstance(data, dict):
        raise ConfigError("%s must contain a JSON object" % path)
    unknown = set(data) - _TOP_LEVEL_KEYS
    if unknown:
        raise ConfigError("unknown top-level keys: %s" % ", ".join(sorted(unknown)))
    jobs = data.get("jobs")
    if not isinstance(jobs, list) or not jobs:
        raise ConfigError("%s: 'jobs' must be a non-empty list" % path)
    data["_base_dir"] = path.parent
    return data


def _platform_list(value) -> Optional[List[str]]:
    if value is None:
        return None
    if isinstance(value, str):
        value = value.replace(",", "+")
        return [p.strip() for p in value.split("+") if p.strip()]
    if isinstance(value, list):
        return [str(p) for p in value]
    raise ConfigError("platforms must be a list or a '+' separated string")


def expand_matrix(
    config: Dict[str, object],
    engines: Optional[Sequence[EngineInstall]] = None,
    registry: Optional[EngineRegistry] = None,
) -> List[BuildRequest]:
    """Expand a matrix config into concrete :class:`BuildRequest` objects.

    Resolution order for options: engine entry > job > defaults > built-ins.
    """
    base_dir = Path(config.get("_base_dir") or ".")
    defaults = config.get("defaults") or {}
    if not isinstance(defaults, dict):
        raise ConfigError("'defaults' must be an object")
    known_engines = list(engines) if engines is not None else all_engines(registry)

    output_root = Path(str(defaults.get("outputRoot") or base_dir / "dist"))
    if not output_root.is_absolute():
        output_root = base_dir / output_root

    requests: List[BuildRequest] = []
    for index, job in enumerate(config["jobs"]):
        if not isinstance(job, dict):
            raise ConfigError("job #%d is not an object" % (index + 1))
        plugin_path = job.get("plugin")
        if not plugin_path:
            raise ConfigError("job #%d is missing 'plugin'" % (index + 1))
        plugin_file = Path(str(plugin_path)).expanduser()
        if not plugin_file.is_absolute():
            plugin_file = base_dir / plugin_file
        descriptor = PluginDescriptor.from_file(plugin_file)
        if descriptor.content_only and not descriptor.can_contain_content:
            raise PluginError(
                "%s has neither C++ modules nor CanContainContent; nothing to build"
                % plugin_file
            )

        engine_specs = job.get("engines") or ["latest"]
        if not isinstance(engine_specs, list):
            engine_specs = [engine_specs]

        # Resolve each spec and keep its per-engine options attached.
        resolved: List = []  # list of (EngineInstall, spec_options_dict)
        for spec in engine_specs:
            if isinstance(spec, dict):
                if "name" not in spec:
                    raise ConfigError(
                        "job #%d engine dicts need a 'name' key" % (index + 1)
                    )
                query, spec_options = str(spec["name"]), spec
            else:
                query, spec_options = str(spec), {}
            engine = resolve_engine(query, engines=known_engines)
            if any(e.root == engine.root for e, _opts in resolved):
                continue
            resolved.append((engine, spec_options))

        for engine, spec_options in resolved:

            def option(key, fallback=None):
                if key in spec_options:
                    return spec_options[key]
                if key in job:
                    return job[key]
                if key in defaults:
                    return defaults[key]
                return fallback

            platforms = _platform_list(option("platforms"))
            output_template = option("output")
            if output_template:
                rendered = str(output_template).format(
                    plugin=descriptor.name,
                    engine=engine.version_str,
                    engineName=engine.name,
                    platforms="+".join(platforms or ["default"]),
                )
                output = Path(rendered)
                if not output.is_absolute():
                    output = base_dir / output
            else:
                output = output_root / descriptor.name / engine.version_str

            requests.append(
                BuildRequest(
                    plugin=descriptor.path,
                    engine=engine,
                    output=output,
                    platforms=platforms if platforms else list(DEFAULT_PLATFORMS),
                    rocket=bool(option("rocket", False)),
                    create_subfolder=bool(option("createSubFolder", False)),
                    no_debug_info=bool(option("noDebugInfo", False)),
                    strict_includes=bool(option("strictIncludes", False)),
                    no_host_platform=bool(option("noHostPlatform", False)),
                    extra_uat_args=dict(defaults.get("extraUatArgs") or {}),
                    logs_dir=output_root.parent / "uebuild-logs",
                    label="%s | %s %s"
                    % (descriptor.name, engine.family_label, engine.version_str),
                )
            )
    return requests
