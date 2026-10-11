# uebuild

Headless **UE4 / UE5 plugin build tool** — a batteries-included wrapper around
Epic's own build automation (`RunUAT BuildPlugin`, the UnrealAutomationTool
command used by the Marketplace/Fab packagers), so plugins can be compiled and
packaged from a terminal or CI runner **without ever opening the Unreal
Editor**.

- 🔎 Discovers UE4 and UE5 installs (launcher, source builds, Windows registry)
- 🧰 Builds plugins headlessly through `RunUAT BuildPlugin` with streamed logs
- 🖥️ One command line on Windows (`.bat`), macOS and Linux (`.sh`)
- 🧱 Build matrices: many engine versions × target platforms from one config
- 📊 Machine-readable JSON + self-contained HTML build reports
- ✅ Strict CI semantics: exit code reflects success; error/warning scraping
- 0️⃣ Runtime dependencies — pure Python 3.9+ standard library

---

## Why BuildPlugin?

`BuildPlugin` is the officially supported way to produce a distributable
plugin package: it compiles every module for each target platform, strips
intermediates, and writes a clean folder (`Binaries/`, `Content/`,
`FilterPlugin.ini`, …) ready for Fab/Marketplace submission or shipping with a
project. The exact invocation this tool runs is:

```bash
# Linux / macOS (everything below is identical for UE4 and UE5)
<engine>/Engine/Build/BatchFiles/RunUAT.sh BuildPlugin \
    -Plugin=/abs/path/MyPlugin.uplugin \
    -Package=/abs/output/dir \
    -TargetPlatforms=Win64+Linux \
    -Rocket -NoP4 -UTF8Output
```

```bat
rem Windows
C:\Program Files\Epic Games\UE_5.3\Engine\Build\BatchFiles\RunUAT.bat BuildPlugin ^
    -Plugin="D:\src\MyPlugin\MyPlugin.uplugin" ^
    -Package="D:\out\MyPlugin" -TargetPlatforms=Win64 -Rocket -NoP4 -UTF8Output
```

`uebuild` discovers the right `RunUAT` for each engine version, builds this
command for you, streams and scrapes the output, and verifies the packaged
result.

## Install

```bash
pip install .          # from this repo — gives you the `uebuild` command
# or run without installing:
PYTHONPATH=src python -m uebuild ...
```

## Quickstart (5 minutes)

### 1. Tell uebuild where your engines are

```bash
uebuild engines add "C:\Program Files\Epic Games\UE_4.27"   # Windows
uebuild engines add "/Users/Shared/Epic Games/UE_5.3"       # macOS
uebuild engines add ~/UnrealEngine                          # Linux source build
uebuild engines add --discover   # scan standard locations + registry + $UE_ROOT
uebuild engines list
```

Engines are detected from `Engine/Build/Build.version`, which both launcher
and source builds ship, so **UE4 and UE5 are handled uniformly**. Registry
lives in `~/.config/uebuild/engines.json` (honours `UEBUILD_CONFIG_DIR`).

### 2. Inspect a plugin

```bash
uebuild plugin info Plugins/MyPlugin/MyPlugin.uplugin
uebuild plugin info Plugins/MyPlugin/MyPlugin.uplugin --engine 5.3   # compat check
```

### 3. Build it, headlessly

```bash
# engine picked automatically from the plugin's EngineVersion field:
uebuild build --plugin Plugins/MyPlugin/MyPlugin.uplugin

# explicit engine + platforms + Fab-ready rocket build:
uebuild build \
    --plugin Plugins/MyPlugin/MyPlugin.uplugin \
    --engine 5.3 \
    --platforms Win64+Linux \
    --rocket --strict-includes --no-debug-info \
    --output dist/MyPlugin/5.3 \
    --report-html dist/report.html --report-json dist/report.json
```

While the build runs, UAT output streams live (errors in red, warnings in
yellow), a full log is written to `uebuild-logs/`, and the packaged
`.uplugin` is verified afterwards. The exit code is `0` on success and `2` on
a failed build, so CI steps fail naturally.

Useful flags:

| Flag | Effect |
| --- | --- |
| `--engine Q` | `5.3`, `4.27`, `UE_5.3`, `latest`, `latest-ue4`, `latest-ue5`, a registry name, or a path |
| `--platforms` | `Win64+Mac+Linux+LinuxArm64+Android+IOS…` (`+` or `,` separated) |
| `--rocket` | binary-distribution ("Rocket") package |
| `--strict-includes` / `--no-debug-info` / `--no-host-platform` / `--create-subfolder` | forwarded to BuildPlugin |
| `--uat-arg K=V` | pass any extra BuildPlugin arg, repeatable (`--uat-arg Unversioned --uat-arg VS2022`…) |
| `--timeout N` / `--no-timeout` | default kill after 4 h |
| `--quiet` | don't stream the log |
| `--dry-run` | print the exact RunUAT command without executing |

### 4. Build a whole matrix

```jsonc
// uebuild.matrix.json — see examples/matrix.example.json
{
  "defaults": {
    "platforms": ["Win64", "Linux"],
    "outputRoot": "dist",
    "rocket": true,
    "strictIncludes": true,
    "extraUatArgs": { "Unversioned": true }
  },
  "jobs": [
    {
      "plugin": "Plugins/MyPlugin/MyPlugin.uplugin",
      "engines": [
        "4.27",
        { "name": "latest-ue5", "platforms": ["Win64", "Mac", "Linux", "LinuxArm64"] }
      ]
    }
  ]
}
```

```bash
uebuild matrix --config uebuild.matrix.json \
    --report-html dist/report.html --report-json dist/report.json
```

One `BuildPlugin` job runs per engine (sequentially — UAT locks the engine
while compiling). `output` templates support `{plugin}`, `{engine}`,
`{engineName}` and `{platforms}` placeholders.

## GitHub Actions / CI

Ready-made recipe for a self-hosted (or large) runner with engines installed:

```yaml
- name: Install uebuild
  run: pip install uebuild  # or: pip install git+https://github.com/aaronprater146-max/agentic
- name: Build plugin for UE4 + UE5
  run: |
    uebuild engines add "C:\Program Files\Epic Games\UE_4.27"
    uebuild engines add "C:\Program Files\Epic Games\UE_5.3"
    uebuild matrix --config uebuild.matrix.json --report-html report.html
- uses: actions/upload-artifact@v4
  with:
    name: plugin-packages
    path: dist/
```

Cross-platform notes:

- Target toolchains must exist on the machine (e.g. the
  [Linux cross toolchain](https://dev.epicgames.com/documentation/en-us/unreal-engine/linux-development-requirements-for-unreal-engine)
  for `Linux` targets on Windows; Xcode for `Mac`/`IOS`; Android SDK/NDK for Android).
- Console platforms (`PS4/PS5/XboxOne/XSX/Switch`) are recognized but require
  the platform holder's SDK; uebuild warns when you request them.
- The process runs strictly headless: stdin is closed, `-NoP4` avoids Perforce
  prompts, and color is auto-disabled when output isn't a TTY (`NO_COLOR`
  respected).

## Exit codes

| Code | Meaning |
| --- | --- |
| `0` | success (`0/n` builds failed) |
| `1` | usage/config/engine/plugin resolution error |
| `2` | one or more builds failed |

## Try it without a 100 GB engine install

The repo ships a fake-engine generator whose stub `RunUAT` emulates
`BuildPlugin` — the same flow used by the test suite and CI smoke job:

```bash
python scripts/make_fake_engine.py demo/UE_5.3 --version 5.3.2
python scripts/make_fake_engine.py demo/UE_4.27 --version 4.27.2
uebuild engines add demo/UE_5.3 && uebuild engines add demo/UE_4.27
uebuild matrix --config demo/matrix.json --report-html demo/report.html

# simulate a compiler failure (exit code 2, red errors, fail report):
UEBUILD_FAKE_UAT_FAIL=error uebuild build \
    --plugin examples/plugins/DummyPlugin/DummyPlugin.uplugin --engine 5.3
```

## Development

```bash
python -m venv .venv && . .venv/bin/activate
pip install pytest
python -m pytest          # 86 tests, all hosts (Linux/macOS/Windows)
```

Layout:

```
src/uebuild/
  engine.py    engine detection (Build.version), discovery, registry, resolution
  plugin.py    .uplugin parsing + validation + engine/platform compatibility
  build.py     BuildPlugin command construction + headless subprocess runner
  logparse.py  UAT/UBT/MSBuild/clang error & warning scraping, exit codes
  matrix.py    JSON matrix config -> concrete BuildRequests
  report.py    JSON + self-contained HTML reports
  cli.py       argparse front-end (`uebuild`)
  testing.py   fake-engine scaffolding for tests/CI (never used in real builds)
tests/         pytest suite (86 tests)
examples/      example plugin + matrix config
scripts/       make_fake_engine.py
demo/          fake engines + matrix config used by the README walkthrough
```

## Limitations

- You still need a real Unreal Engine install (and per-platform toolchains)
  for actual builds — uebuild orchestrates, it doesn't replace, `RunUAT`.
- Building the same engine from two uebuild processes at once is not safe;
  `matrix` therefore runs jobs sequentially.

## License

MIT — see [LICENSE](LICENSE).
