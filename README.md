# agentic

Deep storage and persistent memory for creating high-quality products in Arena. This repository will contain reusable headless tools and finished outputs; Arena downloads only what it needs, saves the result and continuation notes, then removes disposable local tool installations to stay small.

**Agents: read [HANDOFF.md](HANDOFF.md) first.**

## Storage map

- [TOOL_LOG.txt](TOOL_LOG.txt): canonical catalog/log template; download a copy to Arena as `ARENA_LOG.txt`. Do not edit the original during routine use.
- [temporary/WORKLOG.txt](temporary/WORKLOG.txt): latest memory snapshot, overwritten at checkpoints for continuity across chats.
- [temporary/](temporary/): small continuation data, intentionally persisted despite the name.
- [tools/](tools/): headless tools and their instructions, to be developed later.
- [products/](products/): finished products and retrieval information.

Workflow: **read memory → download only what is needed → use tools → save products and overwrite the memory snapshot → verify storage → remove disposable workspace copies**.

## Current status

Connectivity and storage conventions only. No tools are developed or installed, and no products have been created. See the worklog for verification results.

The initial setup is published on `arena/f686d89f-agentic`, not `main`. Until merged, use that branch to retrieve the handoff and latest memory. Work only on the branch assigned to the current Arena session.
