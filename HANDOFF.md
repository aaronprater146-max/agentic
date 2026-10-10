# agentic — agent handoff

## Purpose

`aaronprater146-max/agentic` is this project's **deep-storage repository** and
persistent memory for Arena work. It stores reusable headless tool source,
compact project context, and finished products. Arena is a disposable execution
workspace—not the permanent home of engines, SDKs, dependency caches, or
intermediate output.

**Current implementation:** the first tool,
[`tools/godot-headless/`](tools/godot-headless/), is available. It produces and
confirms a simple Pong proof project inside Godot headlessly. The verified
source product is in [`WORK/arena-pong-v0.1.2/`](WORK/arena-pong-v0.1.2/).
Windows 10/11 and Android 9+ export presets are configured, but no native
binary has been claimed unless its product directory includes a successful
export report.

## Repository layout

| Path | Role |
| --- | --- |
| `HANDOFF.md` | Read first: lifecycle and safety rules for agents. |
| `GOALS.md` | Creative/build goals, delivered scope, and remaining work. |
| `tools/TOOLBOX.md` | Human-readable index of reusable ephemeral tools. |
| `tools/toolbox.json` | Machine-readable toolbox index. |
| `tools/<tool>/` | Reusable source, metadata, tests, template, and usage guide for one tool. |
| `WORK/` | New finished products, compact reports, checksums, and download information. |
| `products/` | Legacy placeholder; do not use it for new products. |
| `TOOL_LOG.txt` | Canonical catalog/template. Do not edit it during routine execution. |
| `temporary/WORKLOG.txt` | Latest compact persistent-memory snapshot. Replace at checkpoints. |
| `temporary/` | Other small, necessary continuation data. It is persisted despite its name. |

## Cold start (start of a chat)

1. Read this handoff from the latest confirmed storage ref, then read
   `GOALS.md`, `temporary/WORKLOG.txt`, `TOOL_LOG.txt`, and the relevant toolbox
   entry.
2. Copy `TOOL_LOG.txt` into the Arena workspace as **`ARENA_LOG.txt`**. This is
   the editable working copy that records actual installs, commands, results,
   product locations, and cleanup.
3. Carry relevant decisions and unfinished work from the saved worklog into the
   working context. Do **not** treat an old installed-tool list as proof that a
   tool exists in this fresh workspace.
4. Select only the tool required for the user’s outcome. Read its `README.md`
   and `TOOL.json`, then download it at the confirmed ref into a marked
   disposable workspace. Prefer a sparse clone or individual-file retrieval;
   do not download/install all tools by default.
5. If no tool is needed, keep the workspace minimal. If a requested tool does
   not exist, develop it deliberately in `tools/` with tests and documentation
   rather than inventing a command.

If running in the managed Git checkout, use it for repository edits/uploads.
Keep an execution copy of the downloaded tool and its runtime outside tracked
paths. A downloaded tool copy is not itself a canonical source edit.

## Toolbox lifecycle

Every reusable tool must document its exact headless entry point, inputs,
outputs, validation, platform constraints, dependency source/version, failure
modes, and cleanup. A normal run is:

1. **Download:** fetch one tool from `tools/` at a known ref into a disposable
   Arena workspace.
2. **Run:** acquire only its required runtime/dependencies in that workspace;
   do not commit them. Preserve enough source/parameters/logs to reproduce the
   product.
3. **Validate:** use the tool’s confirmation/test path and inspect actual
   output. Do not call a configured target a successful binary export without
   an artifact and validation report.
4. **Store:** copy the finished artifact, README, checksums, and compact
   provenance to a descriptive `WORK/<product>/` path.
5. **Publish/link:** commit and push intended storage files, retrieve them from
   GitHub to verify bytes, then provide a direct raw GitHub URL pinned to the
   product commit.
6. **Clean:** only after storage verification, delete the downloaded tool,
   runtime, SDKs, cache, scratch project, and other disposable files from the
   Arena workspace. Never delete canonical `tools/`, `WORK/`, checkout root, or
   `.git`.

## During work

- Run tools headlessly where possible. Follow the documented entry point; do
  not invent commands for tools that do not exist.
- Edit local `ARENA_LOG.txt`, **not** `TOOL_LOG.txt`.
- Record what was installed, where it came from, exact version/hash where
  useful, commands run, outcomes, artifacts, failures, and next steps.
- Never record passwords, tokens, private keys, Android keystores, aliases, or
  signing passwords. Use existing authenticated Git/GitHub access only.
- Changes to toolbox source/catalog are deliberate development work. Add tests
  and update index metadata when a tool changes.
- Treat target configuration and target export separately. For example, a Pong
  project may be configured for Android API 28 while an APK still cannot be
  claimed until matching templates, SDK/JDK, and an actual export are present.

## Save, link, then clean up

At a checkpoint and before ending a chat:

1. Upload products and their compact reports to `WORK/`, with descriptive
   filenames, usage instructions, limitations, hashes, and target status.
2. Update `ARENA_LOG.txt` with actual outcomes and cleanup status. Replace
   `temporary/WORKLOG.txt` from that context; never overwrite `TOOL_LOG.txt`.
3. Review the diff and stage only intended canonical source, product, and
   continuation changes. Publish them on the branch assigned by the
   environment.
4. Verify remote persistence by checking the pushed ref and retrieving the
   stored files. Create the user-facing raw GitHub download link from that
   immutable product commit.
5. Delete only ephemeral workspace copies after verification. Record what was
   removed and what remains in storage.

## Keep storage secure and small

- Do not commit virtual environments, `node_modules`, caches, installed Godot
  runtimes, Android SDK/JDK files, export templates, source-build object files,
  `.godot` import caches, secrets, or signing material.
- Keep `temporary/WORKLOG.txt` concise: current context and exact next steps,
  not a chat transcript.
- Keep product directories self-explanatory. For oversized artifacts, use
  approved external storage and commit the retrieval URL plus integrity data;
  do not silently upload huge binaries.
- Do not remove a user-visible artifact that must remain available in the
  current chat.

## Connectivity and branch rules

- Repository: `https://github.com/aaronprater146-max/agentic`.
- At cold start, use the latest confirmed storage ref named in the saved
  worklog. Do not assume the default branch includes unmerged handoff/memory.
- Always work on the current Arena session branch. Determine it with
  `git branch --show-current`; do not switch branches or push to another one.
- Use `git` for status, diffs, commits, and pushes; use `gh` for GitHub
  operations and individual-file retrieval. Do not exchange credentials in
  chat or logs.
- A local edit alone does not prove persistence. Resolve divergent snapshots
  rather than force-pushing or blindly replacing a newer worklog.

Example, retrieve one handoff file without cloning over a tracked copy:

```sh
storage_ref='your-latest-confirmed-storage-ref'
gh api -H 'Accept: application/vnd.github.raw+json' \
  "repos/aaronprater146-max/agentic/contents/HANDOFF.md?ref=${storage_ref//\//%2F}" \
  > HANDOFF.md
```

## Finish each chat with clear status

Tell the user what was produced, where it is stored, whether remote persistence
was verified, the direct download link (if a product was made), what target
artifacts were or were not actually built, and what temporary workspace state
was removed. Do not claim tools were installed, targets exported, or products
saved unless those actions succeeded.
