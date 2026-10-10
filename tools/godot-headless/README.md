# `godot-headless` — ephemeral Godot 4.7 workflow

A reusable, dependency-light toolbox tool for Arena agents. It scaffolds and
verifies a small Godot project without opening the editor GUI, then bundles the
product source for upload to [`WORK/`](../../WORK/).

> **Lifecycle:** download tool → create a marked disposable workspace → bootstrap
> or supply Godot → scaffold → confirm → bundle/upload to `WORK/` → give the
> user a GitHub download URL → delete the disposable workspace and tool copy.

The repository stores this tool's source and templates only. It never stores a
Godot binary, Android SDK/JDK, export templates, `.godot` cache, signing key, or
other installed dependency.

## What it provides

| Command | Purpose |
| --- | --- |
| `tool-info` | Machine-readable tool metadata and configured platform targets. |
| `workspace-init` / `cleanup-workspace` | Mark and safely remove a disposable Arena work directory. |
| `scaffold-pong` | Copy the standalone Pong proof project into a work directory. |
| `validate` | Check required project files and target configuration without an engine. |
| `bootstrap` | On Linux x86_64, source-build a **temporary 2D confirmation runtime** from Godot 4.7.2. |
| `confirm` | Run the project’s GDScript verification inside Godot headlessly. |
| `export` | Invoke a configured Windows or Android export when all target prerequisites are available. |
| `bundle` | Produce a compact source ZIP, excluding caches, engines, SDKs, templates, and secrets. |

The entry point is [`bin/godot_headless.py`](bin/godot_headless.py). It uses
only the Python standard library at runtime. The source-build fallback installs
`SCons 4.10.1` into the marked temporary work directory and removes it with the
rest of that workspace.

## Download only this tool into Arena

Use a sparse clone so an agent retrieves the toolbox entry rather than a full
working checkout. Set `REF` to the confirmed storage branch or commit before
starting.

```sh
set -eu
REF='arena/2f5538f1-agentic'
FETCH_ROOT="$(mktemp -d)"
WORKSPACE="$(mktemp -d)"
git clone --depth 1 --filter=blob:none --sparse --branch "$REF" \
  https://github.com/aaronprater146-max/agentic.git "$FETCH_ROOT/repo"
git -C "$FETCH_ROOT/repo" sparse-checkout set tools/godot-headless
cp -a "$FETCH_ROOT/repo/tools/godot-headless" "$WORKSPACE/godot-headless"
rm -rf "$FETCH_ROOT/repo"
TOOL="$WORKSPACE/godot-headless/bin/godot_headless.py"
python3 "$TOOL" workspace-init --path "$WORKSPACE/run"
```

The `WORKSPACE` directory now contains only the downloaded tool and its
purpose-specific temporary run directory. Do not download or install unrelated
tools by default.

## Proof workflow: Pong against the computer

The source fallback is intentionally used for **headless confirmation**, not as
a replacement for official export templates. It downloads the pinned Godot
source tag from `codeload.github.com`, installs the pinned SCons build helper
from `pypi.org`, builds a Linux x86_64 2D headless confirmation runtime, and
writes it to the disposable workspace. It is intentionally not used for platform
exports; use a matching full Godot editor plus export templates for that step.

```sh
set -eu
RUN="$WORKSPACE/run"
ENGINE="$RUN/godot-headless"
PROJECT="$RUN/arena-pong"
REPORT="$RUN/confirmation.json"

python3 "$TOOL" bootstrap \
  --destination "$ENGINE" \
  --report "$RUN/bootstrap.json" \
  --jobs 2
python3 "$TOOL" scaffold-pong --output "$PROJECT"
python3 "$TOOL" confirm \
  --godot "$ENGINE" \
  --project "$PROJECT" \
  --report "$REPORT"
python3 "$TOOL" bundle \
  --project "$PROJECT" \
  --confirmation-report "$REPORT" \
  --output "$RUN/ArenaPong-source.zip"
```

A successful `confirm` command exits with status 0 and records
`PONG_CONFIRMATION_PASS`. The in-engine script checks human paddle collision,
computer movement, scoring/reset behavior, and paddle bounds. It is more than a
file-existence check: Godot loads and runs the project’s GDScript headlessly.

## Configured product compatibility

The Pong template uses Godot's Compatibility renderer and has these export
presets:

| Target | Project setting | Build prerequisites |
| --- | --- | --- |
| **Windows 10/11** | `Windows 10/11 x86_64`; 64-bit executable | Matching Godot 4.7.2 Windows export template installed for the supplied editor. |
| **Android 9+** | `Android 9+ (API 28)`; min SDK **28**, `arm64-v8a` + `armeabi-v7a` | Matching Godot 4.7.2 Android export templates, compatible JDK, Android SDK, build tools, and a configured Godot Android environment. |

`export` deliberately checks target prerequisites and returns a report instead
of silently creating a nonfunctional file. Examples, using an externally
provisioned Godot **editor** with matching templates:

```sh
# Windows executable
python3 "$TOOL" export \
  --godot /path/to/godot-editor \
  --project "$PROJECT" \
  --target windows \
  --mode debug \
  --output "$RUN/ArenaPong.exe" \
  --report "$RUN/windows-export.json"

# Android debug APK (ANDROID_SDK_ROOT and Java must be available)
python3 "$TOOL" export \
  --godot /path/to/godot-editor \
  --project "$PROJECT" \
  --target android \
  --mode debug \
  --output "$RUN/ArenaPong.apk" \
  --report "$RUN/android-export.json"
```

Release Android builds require a signing arrangement outside Git. Never put a
keystore, alias, password, or token in this tool, an export preset, a worklog,
or `WORK/`.

## Upload a product and create a download link

After a successful confirmation, copy only the product source ZIP and compact
reports into a descriptive `WORK/` subdirectory. Track source and reports, not
the temporary engine or its dependencies.

```sh
PRODUCT_DIR='WORK/arena-pong-proof'
mkdir -p "$PRODUCT_DIR"
cp "$RUN/ArenaPong-source.zip" "$PRODUCT_DIR/"
cp "$RUN/confirmation.json" "$PRODUCT_DIR/"
cp "$RUN/bootstrap.json" "$PRODUCT_DIR/"
# Add a short README describing the artifact and target status, then commit/push.
```

After the product is pushed, use an immutable commit URL for the user-facing
Arena download link:

```text
https://github.com/aaronprater146-max/agentic/raw/<commit>/WORK/arena-pong-proof/ArenaPong-source.zip
```

A raw GitHub URL downloads the product directly; a `blob/<commit>/...` URL
opens its source page. Always verify the remote bytes before giving the user a
link.

## Cleanup

Only clean after the ZIP/reports are stored and remotely verified. The helper
requires its marker before it will delete a directory:

```sh
python3 "$TOOL" cleanup-workspace --path "$WORKSPACE/run"
rm -rf "$WORKSPACE"
```

This removes the temporary Godot binary, extracted source, SCons dependency,
project cache, reports retained elsewhere, and the downloaded tool copy from
Arena. It does **not** remove the uploaded `WORK/` product or the canonical
toolbox source.

## Test the tool source

These tests do not need Godot or network access; they use a tiny fake engine to
exercise scaffold, validation, confirmation report handling, bundling, and the
safe cleanup marker.

```sh
python3 -m unittest discover -s tools/godot-headless/tests -v
```
