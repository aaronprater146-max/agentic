# Persistent continuation snapshots

This is the temporary workspace handoff area, **not disposable repository data**. Its contents are committed for persistent memory across chats.

- `WORKLOG.txt` is the latest compact snapshot of the editable Arena log. Replace it at checkpoints instead of creating a new log for every chat.
- Place small, necessary continuation files here and reference them in the worklog.
- Keep the user's decisions, current task, outcomes, tool state, product paths, blockers, and next steps.
- Verify a snapshot's upload before deleting the workspace data it replaces.
- Do not upload secrets, full chat transcripts, installed dependencies, caches, or large datasets.
- Delete superseded continuation files only when they are no longer needed; preserve the current worklog.

The original `../TOOL_LOG.txt` is not the running memory log. See `../HANDOFF.md` for the complete workflow.
