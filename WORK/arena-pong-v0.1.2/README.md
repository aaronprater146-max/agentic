# Arena Pong v0.1.2 — headless Godot proof product

## Download

The source bundle was uploaded and retrieved back byte-for-byte from GitHub at
commit [`a0a408a`](https://github.com/aaronprater146-max/agentic/commit/a0a408a07f5d0595d4e1ef2f45a4f781fc4b9f92).

- **Direct download:** [ArenaPong-0.1.2-source.zip](https://github.com/aaronprater146-max/agentic/raw/a0a408a07f5d0595d4e1ef2f45a4f781fc4b9f92/WORK/arena-pong-v0.1.2/ArenaPong-0.1.2-source.zip)
- **Browsable product directory:** [WORK/arena-pong-v0.1.2 at the verified commit](https://github.com/aaronprater146-max/agentic/tree/a0a408a07f5d0595d4e1ef2f45a4f781fc4b9f92/WORK/arena-pong-v0.1.2)
- Artifact: [`ArenaPong-0.1.2-source.zip`](ArenaPong-0.1.2-source.zip)
- SHA-256: `c36e2f1df62c5c3d16ccfa217a654f5284c25859c36f74d09119ee930abf4e3d`
- Integrity manifest: [`CHECKSUMS.sha256`](CHECKSUMS.sha256)

## What is included

The ZIP contains a self-contained Godot 4.7 Pong source project, a deterministic
computer opponent, keyboard/touch controls, Android/Windows export presets, a
headless GDScript confirmation, and a product manifest. It intentionally omits
Godot binaries, SDKs/JDKs, export templates, `.godot` caches, and secrets.

The confirmation/provenance reports beside the ZIP are compact evidence from the
Arena proof run:

- [`confirmation.json`](confirmation.json): Godot 4.7.2 headless confirmation
  passed and emitted `PONG_CONFIRMATION_PASS`.
- [`bootstrap.json`](bootstrap.json): source-build provenance for the temporary
  2D headless runtime, including source/archive and engine hashes.
- [`bundle.json`](bundle.json): product archive size and SHA-256.
- [`tool-info.json`](tool-info.json): toolbox metadata for `godot-headless`
  v0.1.2.

## Verified behavior

The proof ran under a temporary source-built `4.7.2.stable.custom_build` Godot
headless runtime. The in-engine test exercised player-paddle collision, computer
movement, scoring/reset behavior, and paddle bounds; it exited `0` and emitted
the required pass marker.

The minimal template-debug runtime logs `Could not load global script cache.`
because it intentionally has no editor-generated cache. The confirmation tool
records it as a known non-fatal warning only after the engine exits successfully
and emits the pass marker; see `confirmation.json`.

## Platform configuration

| Platform | Configured support | Build status in this proof |
| --- | --- | --- |
| Windows 10/11 | 64-bit `Windows 10/11 x86_64` Godot preset | **Source configured; no `.exe` built.** This Arena worker did not have matching Godot Windows export templates. |
| Android 9+ | API 28 minimum, Compatibility renderer, `arm64-v8a` + `armeabi-v7a` | **Source configured; no APK built.** This Arena worker did not have matching Android templates, Android SDK, or a JDK. |

No placeholder executable or APK was produced. Use the documented
[`godot-headless`](../../tools/godot-headless/README.md) `export` command with a
matching Godot editor/export templates; Android also needs an SDK/JDK and secure
release signing supplied outside this repository.

## Play or continue development

1. Download and unzip the source bundle.
2. Open/import it with Godot 4.7.2 (or use the toolbox `confirm` command).
3. Desktop controls: **W/S** or **Up/Down** for the left paddle. On touch
   devices, touch and drag vertically.
4. To produce a platform binary, use `export_presets.cfg` and the toolbox
   command documented above. Keep signing material outside Git.
