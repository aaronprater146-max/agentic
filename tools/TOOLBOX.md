# Arena toolbox index

The repository’s `tools/` directory is the durable **toolbox**. Each entry is
source and documentation for an **ephemeral** Arena workflow—not an installed
runtime. An agent downloads only the entry needed for the requested result,
uses it in a marked disposable workspace, uploads the finished product to
[`WORK/`](../WORK/), verifies remote storage, gives the user a download link,
and then removes the local tool/runtime/workspace.

Machine-readable metadata lives in [`toolbox.json`](toolbox.json).

## Available tools

| ID | Version | Purpose | Entry point |
| --- | --- | --- | --- |
| [`godot-headless`](godot-headless/README.md) | 0.1.1 | Headless Godot 4.7 Pong scaffold, in-engine confirmation, target-aware export wrapper, and source bundler | `tools/godot-headless/bin/godot_headless.py` |

## Fetch policy

1. Read the tool’s `README.md` and `TOOL.json` before downloading it.
2. Resolve a confirmed repository ref. Use a sparse clone or an individual-file
   retrieval; do not install the whole toolbox by default.
3. Put the downloaded copy and its engine/dependency cache in a marked,
   disposable Arena workspace outside tracked repository paths.
4. Keep reusable source in `tools/`; store only the finished product and small
   provenance/verification reports in `WORK/`.
5. Publish and retrieve the product from GitHub before cleanup. Give the user a
   direct raw GitHub download URL pinned to the product commit.
6. Delete the Arena workspace and downloaded tool copy after the upload is
   verified. Never delete the canonical toolbox source or the uploaded product.

The index records only tools that have a documented headless entry point,
inputs/outputs, validation path, dependency expectations, and cleanup behavior.
