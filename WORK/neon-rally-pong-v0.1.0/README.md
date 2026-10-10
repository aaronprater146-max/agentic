# Neon Rally Pong v0.1.0 — all-tool headless run

## Download

> **Pending first product commit.** This README will gain an immutable,
> commit-pinned raw GitHub download URL after upload and byte verification.

- Artifact: [`NeonRallyPong-0.1.0-source.zip`](NeonRallyPong-0.1.0-source.zip)
- SHA-256: `fe1273717ba80cb87bd8d419e4f38335166787ab847ac86fb0f903f6f945cdd5`
- Integrity manifest: [`CHECKSUMS.sha256`](CHECKSUMS.sha256)

## What makes this Pong distinct

**Neon Rally Pong** is a new variation generated from the headless Pong scaffold
and customized in the disposable Arena workspace before confirmation:

- violet neon court, mint player paddle, magenta computer paddle, and neon ball;
- faster serve and player response, a slightly more forgiving computer, and a
  higher maximum rally speed;
- Windows 10/11 x86_64 and Android 9+ (API 28, `arm64-v8a` + `armeabi-v7a`)
  export presets with a distinct package name and artifact paths.

The source ZIP includes `PRODUCT_VARIANT.md`, project source, export presets,
the headless in-engine test, and the product manifest. It excludes Godot
binaries, SDK/JDK files, export templates, `.godot` caches, and secrets.

## Every available toolbox command was exercised

The only current toolbox entry is `godot-headless` v0.1.3. This product used its
complete workflow:

| Command | Result |
| --- | --- |
| `tool-info` | Recorded v0.1.3 metadata in `tool-info.json`. |
| `workspace-init` | Marked the disposable Arena run directory for safe cleanup. |
| `scaffold-pong` | Generated the starting Godot project. |
| `validate` | Confirmed required project files, Windows x86_64, and Android API 28 configuration. |
| `bootstrap` | Source-built a temporary Godot 4.7.2 2D headless runtime. |
| `confirm` | Passed in-engine GDScript confirmation and emitted `PONG_CONFIRMATION_PASS`. |
| `export --target android` | Correctly stopped before output because Android SDK/JDK variables were absent. |
| `export --target windows` | Correctly failed rather than emitting a placeholder binary; the compact confirmation runtime is not a full Windows export editor/template installation. |
| `bundle` | Created this verified source artifact with the project’s actual display name and slug. |
| `cleanup-workspace` | Runs after remote persistence is verified; its result is recorded in the project worklog. |

The reports named in the table are stored beside the artifact. The expected
failed export preflights are evidence of dependency checks, **not** native
binary builds.

## Verified engine result

The confirmation ran with a temporary source-built
`4.7.2.stable.custom_build` Godot runtime. It exited zero and tested collision,
computer movement, scoring/reset, and paddle bounds. A separate headless preload
of the customized `scripts/main.gd` also passed; see
[`main-script-parse.json`](main-script-parse.json). The compact confirmation
runtime may log the known missing global-script-cache warning because it has no
editor-generated cache; the confirmation tool classifies it as non-fatal only
when the pass marker and exit code zero are both present.

## Target status

No fake `.exe`, APK, or AAB is included.

- **Windows 10/11:** project/preset configured; a full matching Godot editor and
  Windows export templates are still required for a real `.exe`.
- **Android 9+:** project/preset configured with min SDK 28; matching Godot
  Android templates, a compatible JDK, Android SDK/build tools, and signing
  setup are still required for a real APK/AAB.

Use the documented [`godot-headless`](../../tools/godot-headless/README.md)
export command from a freshly marked disposable workspace once those target
prerequisites are supplied.
