# agentic — Current Goals

> **From editable scenes and layers to playable, distributable products.**

Build a compact suite of **headless tools operated by Arena agents**: create visual assets, assemble Godot projects, and produce usable builds. The tools are not a separate end-user application and must not depend on clicking through desktop editors.

**Status:** Goals recorded · implementation plan comes next · no tools built yet

**Updated:** October 10, 2026

---

## The capability we want

| Area | Desired outcome | Scope |
| --- | --- | --- |
| **Blender** | Scripted 3D asset creation, scene editing, and rendering | Confirmed goal |
| **Layered images** | Editable 2D artwork and compositing without Stable Diffusion | Confirmed goal |
| **Godot** | Turn assets and project source into playable, exportable products | Confirmed goal |
| **Android SDK & builds** | Produce Android packages through a headless build workflow | Confirmed goal |
| **Windows executables** | Potential Windows exports and `.exe` packaging | Optional; scope later |

These are intended capabilities, **not features that already exist**.

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

## 04 · Android SDK and build capability

Support Android production as part of the tool suite, not as an undocumented manual step.

Desired capabilities include:
- Provision the required Android SDK command-line components, Java environment, and any additional build dependencies required by the selected Godot workflow.
- Configure Android exports and build testable APKs, with AAB output when distribution requires it.
- Separate debug builds from release builds and validate package outputs.
- Handle release signing securely: credentials and private signing material must never be committed or copied into the worklog.

**Outcome:** A documented, repeatable headless path from a Godot project to an Android package.

Compatible versions, reachable dependency sources, storage requirements, and signing arrangements must be confirmed during planning. No Android build support is claimed yet.

## 05 · Possible Windows `.exe` creation

Explore Windows desktop exports and executable packaging, including Godot Windows builds. This is a **possible extension**, not a confirmed first-delivery requirement.

The later plan should establish:
- Whether the goal is Godot exports only or also packaging other application types.
- Which outputs can be built from Arena's host environment and which tasks would require a Windows environment.
- What runtime files, packaging metadata, validation, and optional signing are needed for a usable release.

**Outcome, if pursued:** A distributable Windows executable or package with documented contents and limitations—not merely a file renamed to `.exe`.

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

**Agree on an implementation plan before developing or installing the tools.** That discussion will choose priorities, a first end-to-end demonstration, tool interfaces, dependency sources and versions, validation criteria, and platform constraints.

This file records the current vision. It does not select every library, prescribe a build sequence, or authorize implementation yet.
