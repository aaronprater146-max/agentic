# agentic — agent handoff

## Purpose

`aaronprater146-max/agentic` is this project's **deep-storage repository** and persistent memory for work done in Arena. It will hold reusable headless tools, compact project context, and finished products. Arena is a small, disposable execution workspace, not the permanent home of those assets.

**Current scope: connectivity and documentation only.** No tools have been developed or installed. Do not build or install tools until the user requests them.

## Repository layout

| Path | Role |
| --- | --- |
| `HANDOFF.md` | Read first: how an agent should use this repository. |
| `TOOL_LOG.txt` | Canonical tool catalog and starting template for the editable Arena log. Routine workspace activity must not edit this original. |
| `temporary/WORKLOG.txt` | Latest persistent-memory snapshot. Replace its contents at checkpoints; do not create a new worklog per chat. |
| `temporary/` | Other small, necessary continuation data. Despite its name, committed data here is persistent. |
| `tools/` | Reusable headless tool source and usage instructions, to be developed later. |
| `products/` | Finished outputs and the information needed to find and use them. |

## Start of a chat

1. Read this handoff from the latest saved storage ref, then read `temporary/WORKLOG.txt` and `TOOL_LOG.txt`.
2. Download `TOOL_LOG.txt` into the Arena workspace as **`ARENA_LOG.txt`**. This is the working copy: the chat edits it to record tool availability, local installs, usage, outcomes, product locations, and continuation notes.
3. Bring relevant context from the saved worklog into the working copy. Preserve useful decisions and unfinished work, but do not treat a previous chat's installed-tool list as proof that those tools are installed now. Check the actual workspace.
4. Retrieve only the tools, inputs, and dependencies needed for the requested outcome. Prefer individual-file downloads over bringing all deep storage into Arena. Do not install the entire tool suite by default.
5. If no tools are needed, keep the workspace minimal and do not install any.

If running inside the existing managed Git checkout, use it for uploads rather than making another clone. Keep transient installations outside tracked storage paths. A downloaded copy of a repository file is not automatically a change to its canonical source.

## During work

- Run tools headlessly where possible. Follow each tool's documented entry point, inputs, outputs, and dependencies; never invent a command for a tool that has not been built.
- Edit the local `ARENA_LOG.txt`, **not** the original `TOOL_LOG.txt` in the repository.
- Record what was installed, where it came from, how it was used, and whether it has since been removed. Include artifact paths, useful decisions, errors, and the next action.
- Do not record passwords, tokens, private keys, or unnecessary personal data. Use existing authenticated Git/GitHub access; never put credentials in logs.
- Changes to the canonical catalog or reusable tool source are deliberate development work, not a side effect of using a tool. Make them only when requested.

## Save, then clean up

At a checkpoint and before ending a chat:

1. Upload finished products to `products/` and the small continuation files needed by the next chat to `temporary/`. Give products descriptive names and retain their usage/provenance information.
2. Update the working `ARENA_LOG.txt` with actual outcomes, storage paths, active blockers, and exact next steps.
3. Copy the working log to **`temporary/WORKLOG.txt`**, replacing the current snapshot. Do not copy it over `TOOL_LOG.txt`. The latest worklog is compact current memory; Git history retains prior committed snapshots.
4. Review the diff, stage only intended storage changes, and publish them using Git on the branch assigned by the environment. Verify the remote commit/files before treating the save as complete. If publishing fails, retain the local files and report that remote persistence is not confirmed.
5. Only after the required files are safely stored and retrievable, remove downloaded tool copies, installed tool dependencies, scratch inputs, and generated intermediates from the Arena workspace when they are no longer needed. Record the cleanup and publish the updated worklog if it changes.

Delete workspace copies, **not** the reusable tools, stored products, or persistent memory in this repository. Never delete the managed checkout root or its `.git` directory. Avoid removing an output that still needs to remain available to the user in the current chat.

## Keep storage and workspace small

- Do not commit virtual environments, `node_modules`, caches, secrets, or dependency downloads. Store tool source and dependency manifests instead.
- Keep `temporary/WORKLOG.txt` concise: current context and next steps, not a transcript of every chat.
- Store only continuation data worth carrying forward. Remove superseded temporary data deliberately, without deleting the current snapshot.
- For a product too large for the repository/platform limits, use an approved artifact or external-storage location and record its retrieval link and integrity information here. Do not silently commit large datasets or binaries.

## Connectivity and branch rules

- Repository: `https://github.com/aaronprater146-max/agentic`.
- The initial setup is on **`arena/f686d89f-agentic`**. Until it is merged into `main`, read this handoff and memory from that branch; do not assume the default branch has the latest files.
- Always work on the branch assigned to the current Arena session. In this session it is `arena/f686d89f-agentic`; do not switch branches, create another working branch, or push elsewhere.
- Use `git` for status, diffs, commits, and pushes; use `gh` for GitHub operations and individual-file retrieval. No credential sharing in chat is needed.
- A local edit alone does not prove remote persistence. The worklog must distinguish local checks from a confirmed GitHub upload/download.
- Resolve divergent snapshots before overwriting them; do not force-push or blindly replace another chat's newer memory. If a session branch is not merged, state where its latest snapshot lives so a later chat can retrieve it.

Example: download just the initial handoff without cloning the repository (run from a scratch/workspace directory, not over the canonical tracked file):

```sh
gh api -H 'Accept: application/vnd.github.raw+json' \
  'repos/aaronprater146-max/agentic/contents/HANDOFF.md?ref=arena%2Ff686d89f-agentic' \
  > HANDOFF.md
```

Use the same retrieval pattern for `TOOL_LOG.txt`, saving it locally as `ARENA_LOG.txt`, and for `temporary/WORKLOG.txt`. Substitute the latest confirmed storage ref when appropriate.

## Finish each chat with a clear status

Tell the user what was produced, where it is stored, whether remote persistence was verified, and what was removed from Arena. Leave enough memory for another chat to continue without guessing. Do not claim that tools were installed, products were created, or data was saved unless those actions actually succeeded.
