# Arena Agent — Arena.ai's Unreal Engine Agent Plugin

**Arena Agent** turns the Unreal Editor into an agentic workspace. A persistent chat panel is wired to
the Arena.ai API (any OpenAI-compatible endpoint works), and the model drives the editor through a set of
real tools — creating Blueprints of every type, adding components / variables / functions / events,
wiring nodes, spawning actors, managing assets and (optionally) running Unreal Python.

> "Let's create an advanced RPG system" → the agent plans, creates the Blueprints, stats, functions,
> events and data tables, verifies its own work, and summarizes what it built.

Target engine: **Unreal Engine 5.8.x** (built for 5.8.3). Editor-only; safe to ship in any project
(no runtime module, no content).

---

## Features

- **Persistent chat panel** — dockable tab; closing it never loses state (all state lives in a module-level runner).
- **Saved conversations** — every conversation is stored as JSON under `<Project>/Saved/ArenaAgent/Conversations/`.
  The sidebar lists them (most recent first) with **New / Rename / Delete / Clear All**.
- **Clearable history** — *Clear History* wipes the current conversation's messages.
- **Full agent loop** — the model can chain tool calls (default: up to 16 iterations per message),
  gets the tool results back and keeps going until it produces a final answer.
- **Blueprint surgery from code** — create Actor/Character/Pawn/GameMode/Widget BPs, add SCS components
  with transforms, typed variables (incl. arrays, object refs, enums), functions with typed pins,
  event nodes (BeginPlay, Tick, overlaps, damage, …) and wired *Call Function* nodes. Everything is compiled
  synchronously after each mutation so the editor stays consistent.
- **Self-verification** — `get_blueprint_info` returns the full structure of a BP so the model can check its work.
- **Level interaction** — spawn actors into the editor level, inspect the current level and selection.
- **Asset management** — list/search/rename/duplicate/delete/open assets, create folders and DataTables.
- **Python escape hatch** — `run_python` executes editor Python for anything the dedicated tools can't express
  (disabled by default — flip *Allow Python Execution* in settings).

## Install

1. Copy the `ArenaAgent` folder into `<YourProject>/Plugins/` (create `Plugins` if needed).
2. Regenerate project files and build (or just launch the editor — it will offer to compile).
3. In the editor: **Edit → Plugins → "Arena Agent"** is enabled automatically (it also enables the
   Python Script Plugin, which ships with the engine).
4. Configure: **Edit → Project Settings → Plugins → Arena Agent**:
   - **API Base URL** — any OpenAI-compatible chat-completions endpoint (default `https://api.arena.ai/v1`).
   - **API Key** — your key (or set the `ARENA_API_KEY` environment variable instead).
   - **Model** — model name the endpoint expects.
   - Optional: system prompt, iteration limit, context size, auto-save, Python permission, default asset folder.
5. Open the chat: **Window → Arena Agent Chat** (or the *Arena Agent* toolbar button).

## Talking to the agent

Just describe what you want:

- *"Create an advanced RPG system: a character BP with health/mana/stamina, an inventory component,
  level-up function, XP events, and a data table for items."*
- *"Make a BP_Door actor that opens on overlap and plays a sound."*
- *"Spawn three of them around the level."*

The agent will call its tools, read the results, and report back with the created asset paths.

## Tool reference

| Tool | Purpose |
| --- | --- |
| `get_editor_context` | Current level, selected actors, default asset folder. |
| `create_blueprint` | New BP of any Actor-derived or UserWidget-derived parent class. |
| `add_component` | SCS component (class, name, attach-to, relative transform). |
| `add_variable` | Typed variable (float/int/bool/string/name/text/vector/rotator/transform/color/object/enum, arrays). |
| `add_function` | Function graph with typed input/output pins and entry→result exec chain. |
| `add_event` | Event node in the EventGraph (BeginPlay, Tick, ActorBeginOverlap, …). |
| `add_call_node` | Call Function node appended to an exec chain (event or function anchor, literal pin values). |
| `compile_blueprint` | Force recompile. |
| `get_blueprint_info` | Full structure dump (components, variables, functions, events) as JSON. |
| `spawn_actor` | Spawn a BP/class instance into the editor level. |
| `list_assets` | Browse content paths with class filters. |
| `search_classes` | Discover class paths by name / base class. |
| `create_folder` | Create content folders. |
| `create_data_table` | Empty DataTable with a given row struct. |
| `rename_asset` / `duplicate_asset` / `delete_asset` / `open_asset` | Asset management. |
| `run_python` | Editor Python (gated by settings). |

Conversations are saved under `Saved/ArenaAgent/Conversations/` — safe to back up or delete.

## Notes & limitations

- The plugin uses stable editor APIs, but Epic occasionally renames things between point releases.
  If a single symbol fails to compile on your exact engine build, the offending call is isolated in
  `Source/ArenaAgent/Private/ArenaBlueprintUtils.cpp` (graph surgery), `ArenaToolRegistry.cpp` (asset tools)
  or `ArenaApiClient.cpp` (HTTP) — each is a one-line swap.
- Object-reference pin defaults and complex pin wiring (e.g. wiring data pins between nodes) are best done
  through `run_python` — that path can express literally anything the editor UI can.
- `delete_asset` uses the standard editor deletion flow, so the editor may show its confirmation dialog.
- The chat is intentionally non-streaming: requests complete, tool calls execute, the loop continues.
