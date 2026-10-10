# Reusable headless tools — Arena toolbox

This directory is the durable **toolbox** for source-controlled, headless tools
that Arena agents download only when needed. It does not contain installed
runtimes, SDKs, caches, or generated products.

Start with the [toolbox index](TOOLBOX.md) and its machine-readable
[`toolbox.json`](toolbox.json). Each tool must include:

- `TOOL.json`: stable ID, version, capabilities, platform constraints, and
  runtime/dependency metadata;
- a README with exact headless entry point, inputs, outputs, verification,
  target prerequisites, and cleanup instructions;
- source/templates and automated tests that do not require a GUI;
- a lifecycle that uploads the verified product to [`../WORK/`](../WORK/) and
  makes a commit-pinned GitHub raw download link available to the user.

## Rules for Arena agents

1. Download only the required tool at a confirmed repository ref—prefer a
   sparse clone or individual-file retrieval over cloning/installing all tools.
2. Put the downloaded tool, runtime, SDKs, and generated intermediates in a
   marked disposable workspace outside tracked repository paths.
3. Run tools headlessly; preserve source, parameters, reports, and test results
   needed to reproduce a finished product.
4. Upload the small finished product and compact provenance to `WORK/`, push,
   retrieve it back from GitHub, then give the user the direct raw download URL.
5. Only after remote verification, delete the downloaded tool copy and all
   disposable local dependencies. Never delete this canonical `tools/` source,
   `WORK/` products, the checkout root, or `.git`.

The first available entry is [`godot-headless`](godot-headless/README.md),
which builds and confirms a simple Pong proof project through Godot headlessly.
