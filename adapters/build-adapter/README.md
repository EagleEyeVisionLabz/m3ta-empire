# build-adapter

A runtime adapter that hands off code-shaped tasks (scaffolding, refactors,
test writing, file edits) from the M3ta-OS orchestration layer to an external
build agent process, and brings the results back through the same memory and
audit surfaces the rest of the stack uses.

The adapter is configuration plus glue — it does not embed the build agent
itself. It defines a stable handoff contract so the build runtime can be
swapped without disturbing upstream callers.

## Four-layer architecture

| Layer            | Responsibility                                                |
| ---------------- | ------------------------------------------------------------- |
| Identity         | Who is calling, what role, what scopes are in play            |
| Tool plane       | MCP servers (Notion, Slack, Attio, Obsidian), repo intel, CLI |
| Runtime adapter  | The external build agent process, sandbox, IO contract        |
| Memory & audit   | Obsidian log sink, Slack alert channel, Notion task ledger    |

Each layer is addressable on its own and survives a swap of any other layer.
Identity does not need to know which build runtime is wired in; the build
runtime does not need to know which memory sink is recording the session.

## Routing summary

Build-shaped verbs route here. Strategy-shaped verbs do not.

| Verb family                                           | Destination               |
| ----------------------------------------------------- | ------------------------- |
| build, scaffold, generate, write, refactor, port      | build-adapter (this dir)  |
| test, lint, fix-up, codemod                           | build-adapter (this dir)  |
| analyze, plan, strategize, decide, compare            | orchestration layer       |
| recall, summarize, look up                            | memory layer first        |
| ship, release, tag, merge                             | release tooling           |

See `router/task-classifier.ts` for the executable rules.

## File map

- `BOOTSTRAP.md` — installation, environment, first-run smoke check
- `PROMPT.md` — the system prompt loaded into the external build agent
- `RUNBOOK.md` — standard commands, error recovery, monitoring touchpoints
- `mcp-config.json` — MCP endpoint stubs (Notion, Slack, Attio, Obsidian)
- `.env.example` — environment variable template; copy to `.env` and fill
- `router/task-classifier.ts` — verb-based router with `model_route` hints
- `scripts/build-*.sh` — five CLI wrappers (init, plan, exec, doc, sync)
- `templates/` — task templates for common operations

## Status

Scaffold only. No build runtime is wired in yet. The handoff contract,
prompt surface, and CLI shape are defined here so that the runtime swap is
a configuration change rather than a refactor.
