# agentic

Durable deep storage for Arena-operated, headless production tools and their
verified products. Arena downloads only the tool it needs, runs it in a
disposable workspace, uploads the result and compact provenance to this
repository, verifies the remote copy, gives the user a download URL, and then
removes the local runtime/tool copy.

**Agents: read [HANDOFF.md](HANDOFF.md) first.**

## Current delivery

The first reusable toolbox entry is
[`godot-headless`](tools/godot-headless/README.md) **v0.1.3**. It provides a
headless Godot 4.7 workflow that can:

- scaffold a small Pong game against a computer opponent;
- validate its Windows 10/11 and Android 9+ export configuration;
- source-build a temporary Linux headless confirmation runtime when an engine
  binary is unavailable;
- run an in-engine GDScript confirmation and require `PONG_CONFIRMATION_PASS`;
- bundle a compact source product and safely clean the marked Arena workspace;
- invoke Windows/Android exports when matching templates and target SDK tools
  are provisioned.

Verified source products now include:

- [`Arena Pong v0.1.2`](WORK/arena-pong-v0.1.2/), the baseline proof; and
- [`Neon Rally Pong v0.1.0`](WORK/neon-rally-pong-v0.1.0/), a faster neon
  variation that exercised every available `godot-headless` workflow command.

Both products passed the in-engine headless confirmation and are **configured**
for Windows 10/11 x86_64 and Android 9+ (API 28, `arm64-v8a` and
`armeabi-v7a`). No fake `.exe` or `.apk` is included: this Arena worker lacks
matching export templates and, for Android, the SDK/JDK. Each product README
states its exact status and download link after remote verification.

## Storage map

- [HANDOFF.md](HANDOFF.md): agent lifecycle, cold-start instructions, and
  cleanup/publishing rules.
- [GOALS.md](GOALS.md): current capability goals and delivered/pending scope.
- [tools/TOOLBOX.md](tools/TOOLBOX.md): human-readable toolbox index.
- [tools/toolbox.json](tools/toolbox.json): machine-readable toolbox index.
- [tools/godot-headless/](tools/godot-headless/): first reusable tool source,
  template, metadata, tests, and usage guide.
- [WORK/](WORK/): finished, downloadable products and compact provenance. New
  products belong here.
- [TOOL_LOG.txt](TOOL_LOG.txt): canonical tool catalog and starting template
  for the editable Arena log. Routine workspace activity must not edit it.
- [temporary/WORKLOG.txt](temporary/WORKLOG.txt): latest persistent-memory
  snapshot, replaced at checkpoints.
- [products/](products/): legacy placeholder retained for older references;
  new outputs go to `WORK/`.

## Standard toolbox workflow

1. Read the handoff, worklog, toolbox index, and selected tool’s README.
2. Download only that tool at a confirmed storage ref into a marked disposable
   Arena workspace; do not install the whole toolbox.
3. Run the tool headlessly, validate the output, and record actual dependency
   and command outcomes in the local `ARENA_LOG.txt`.
4. Copy only the finished product and compact reports to a descriptive `WORK/`
   subdirectory. Never upload engine binaries, SDKs, caches, or credentials.
5. Commit/push the intended files, retrieve them from GitHub to verify bytes,
   and give the user a commit-pinned raw GitHub download URL.
6. Delete the marked Arena workspace and downloaded tool/dependency copies only
   after persistence is verified.

The goal is reproducible products without treating Arena’s execution workspace
as durable storage.
