# Agent instructions

Read `HANDOFF.md`, `temporary/WORKLOG.txt`, and the relevant toolbox entry
before doing work.

- This repository is deep storage; keep the Arena execution workspace small.
- The durable toolbox lives in `tools/`. Download only the requested entry at a
  confirmed ref into a marked disposable workspace; do not install all tools.
- `TOOL_LOG.txt` is canonical. Download it as local `ARENA_LOG.txt` and edit
  that working copy, not the canonical catalog.
- Use tools headlessly. Record actual dependency versions, command outcomes,
  validation, artifact paths, and cleanup in the working log.
- Upload new finished products and compact provenance to `WORK/`, not the
  legacy `products/` placeholder. Push, retrieve, and verify them before giving
  the user a commit-pinned raw GitHub download URL.
- At checkpoints, replace `temporary/WORKLOG.txt` from the working context and
  verify remote persistence before deleting local artifacts.
- Do not commit engines, SDKs, JDKs, export templates, dependency folders,
  caches, secrets, signing keys, or generated intermediates unless explicitly
  approved storage rules say otherwise.
- Work only on the current session's assigned branch. Use the latest confirmed
  storage ref for unmerged handoff/worklog data rather than assuming `main` has
  it.
- Do not delete stored tools, `WORK/` products, memory, the checkout root, or
  `.git` as part of workspace cleanup.
