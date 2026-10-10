# Agent instructions

Read `HANDOFF.md` before doing any work, then read `temporary/WORKLOG.txt` for the latest persistent memory.

- This repository is deep storage; keep the Arena execution workspace small.
- Download `TOOL_LOG.txt` as a local `ARENA_LOG.txt` and edit that copy, not the canonical original.
- At checkpoints, store outputs and continuation data, replace `temporary/WORKLOG.txt`, and verify remote persistence before removing needed local files.
- Do not build or install tools until the user requests that work.
- Work only on the current session's assigned branch. Use the latest confirmed storage ref for any unmerged handoff, rather than assuming `main` has it.
- Do not delete stored tools, products, memory, the checkout root, or `.git` as part of workspace cleanup.
