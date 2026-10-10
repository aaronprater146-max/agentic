# agentic — Current Goals

> **From editable scenes and layers to playable, distributable products.**

Build a compact suite of **headless tools operated by Arena agents**: create visual assets, assemble Godot projects, and produce usable builds. The tools are not a separate end-user application and must not depend on clicking through desktop editors.

**Status:** First headless Godot tool and Pong source proof delivered · native target exports pending environment prerequisites

**Updated:** October 10, 2026

---

## The capability we want

| Area | Desired outcome | Scope |
| --- | --- | --- |
| **Blender** | Scripted 3D asset creation, scene editing, and rendering | Confirmed goal |
| **Layered images** | Editable 2D artwork and compositing without Stable Diffusion | Confirmed goal |
| **Godot** | Turn assets and project source into playable, exportable products | First tool/proof delivered |
| **Android SDK & builds** | Produce Android packages through a headless build workflow | Target configured; SDK/build proof pending |
| **Windows executables** | Produce Windows 10/11 x86_64 exports | Pong target configured; binary proof pending |

Except for the documented Godot/Pong proof milestone below, these remain intended capabilities—not claims that the full tool suite already exists.

## 01 · Blender automation

Use Blender as a programmable production tool rather than a manually operated editor.

Desired capabilities include:
- Create and modify geometry, materials, lights, cameras, and reusable scenes.
- Produce polished renders, transparent assets, and visual variations from saved parameters.
- Prepare assets for Godot, including compatible exports and predictable scale, orientation, and naming.
- Preserve editable scene source alongside final renders or exported assets.

**Outcome:** An Arena agent can request an asset or scene, run a documented headless tool, and receive both a finished output and the source needed to revise it.

## 02 · Layered image creation and editing

Create images through **authored graphics, procedural drawing, Blender renders, and layer-based composition instead of Stable Diffusion**. A diffusion-model image pipeline is not part of the current goal.

Desired capabilities include:
- Create and edit raster/vector elements, shapes, typography, and textures.
- Work with layers and groups, transforms, masks, transparency, blending, and compositing.
- Combine rendered 3D elements with 2D artwork to produce icons, UI graphics, textures, and other product assets.
- Save editable layered source and export finished images or individual layers.

**Outcome:** Visual assets are controllable and revisable—not just flattened images. Their construction can be recorded and reproduced where practical.

The layered document format and editing engine are deliberately undecided until planning.

## 03 · Godot production tools

Provide the supporting tools needed to turn our assets and project source into working Godot products without relying on the editor GUI.

Desired capabilities include:
- Create and modify project structure, scenes, resources, scripts, and asset references.
- Import and validate 2D/3D assets, with useful diagnostics for missing files or incompatible settings.
- Run headless project checks and automated tests appropriate to the chosen workflow.
- Manage compatible export templates and presets, then package builds with clear logs and output locations.

**Outcome:** An Arena agent can move from project source and assets to a checked, exportable Godot project and supported target builds.

**Current milestone:** `tools/godot-headless` v0.1.2 scaffolds a Pong proof,
validates its target presets, source-builds a temporary Linux headless confirmation
runtime when necessary, runs an in-engine GDScript test, and bundles the verified
source product. The first result is `WORK/arena-pong-v0.1.2/`. This proves the
engine/GDScript workflow—not a Windows or Android binary export.

## 04 · Android SDK and build capability

Support Android production as part of the tool suite, not as an undocumented manual step.

Desired capabilities include:
- Provision the required Android SDK command-line components, Java environment, and any additional build dependencies required by the selected Godot workflow.
- Configure Android exports and build testable APKs, with AAB output when distribution requires it.
- Separate debug builds from release builds and validate package outputs.
- Handle release signing securely: credentials and private signing material must never be committed or copied into the worklog.

**Outcome:** A documented, repeatable headless path from a Godot project to an Android package.

The current Pong preset explicitly sets Android API 28 (Android 9+) as the
minimum SDK and includes `arm64-v8a` plus `armeabi-v7a`. The tool can invoke a
headless Android export when matching Godot templates, a compatible JDK, and an
Android SDK are supplied. This Arena proof did **not** have those dependencies,
so no APK/AAB is claimed yet. Release signing remains external and must never be
committed or copied into logs.

## 05 · Possible Windows `.exe` creation

Support Windows 10/11 desktop exports and executable packaging, beginning with
the Godot Pong workflow. The current proof includes a 64-bit Windows Desktop
export preset, but it does not claim a binary until a matching export template
produces and validates one.

The later plan should establish:
- Whether the goal is Godot exports only or also packaging other application types.
- Which outputs can be built from Arena's host environment and which tasks would require a Windows environment.
- What runtime files, packaging metadata, validation, and optional signing are needed for a usable release.

**Outcome:** A distributable Windows 10/11 x86_64 executable or package with
documented contents and limitations—not merely a file renamed to `.exe`.

---

## How the suite must work

- **Arena-operated and headless.** Use documented scripts, command-line interfaces, or APIs. The tools need no interactive GUI; the finished products may still be graphical.
- **Small workspace, durable storage.** Retrieve only what a task needs. Save sources, products, and continuation notes, verify storage, then remove disposable local installations and intermediates.
- **Editable and reproducible.** Retain source documents, parameters, dependency/version information, and instructions sufficient to continue or regenerate the work.
- **Clear outcomes.** Report success or failure, actionable logs, and exact artifact locations. Validate outputs before calling them finished.
- **Persistent memory.** Edit the downloaded Arena log, preserve the canonical `TOOL_LOG.txt`, and overwrite `temporary/WORKLOG.txt` at checkpoints.
- **No bulky installations in Git.** Store tool code, manifests, and instructions—not installed Blender/Godot runtimes, full SDKs, dependency folders, or caches. Large deliverables follow the repository's approved artifact-storage conventions.

See [HANDOFF.md](HANDOFF.md) for the complete storage and cleanup lifecycle.

## What comes next

**The first Godot/Pong proof is now authorized and delivered.** Next, provision
matching Godot export templates plus the Android SDK/JDK in a disposable Arena
workspace, use the existing export wrapper to produce/validate a Windows x86_64
binary and Android APK, then store only finished artifacts and compact reports
in `WORK/`. After that, choose the next tool priority (asset creation, layered
images, or wider Godot automation).

This file records the current vision and delivered status. It does not authorize
committing bulky runtimes, SDKs, caches, or signing material.
