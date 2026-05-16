# Bootstrap

How to bring `adapters/build-adapter/` from a fresh checkout to a working
local install. Read top-to-bottom on first install; later sessions only need
the smoke check at the end.

## Prerequisites

- macOS or Linux. Windows via WSL2 only.
- Bun >= 1.1 (the rest of `m3ta-empire` uses Bun; align with the kernel).
- Node 20+ available as a fallback for tooling that needs it.
- `jq` and `curl` on the PATH.
- A working LiteLLM proxy at `http://localhost:4000/v1` (the M3ta-OS routing
  backbone). Verify with `curl -sS http://localhost:4000/health`.
- A reachable Obsidian vault path for the audit sink.
- API keys for whichever MCP backends you plan to wire up (Notion, Slack,
  Attio). Obsidian is filesystem-only.

If any prerequisite is missing, stop and install it. Do not substitute.

## File install

The adapter lives under `adapters/build-adapter/` in the `m3ta-empire`
monorepo. Nothing is published as a package — every file is read in place.

```
adapters/build-adapter/
  README.md
  BOOTSTRAP.md
  PROMPT.md
  RUNBOOK.md
  mcp-config.json
  .env.example
  router/
    task-classifier.ts
  scripts/
    build-init.sh
    build-plan.sh
    build-exec.sh
    build-doc.sh
    build-sync.sh
  templates/
    task-scaffold.md
    task-refactor.md
```

## Environment

Copy the example file and fill in real values. The example file is checked
in; the real `.env` is git-ignored.

```bash
cp adapters/build-adapter/.env.example adapters/build-adapter/.env
$EDITOR adapters/build-adapter/.env
```

Required variables at minimum:

- `EXTERNAL_BUILD_AGENT_API_KEY` — credential for the external build runtime
- `EXTERNAL_BUILD_AGENT_ENDPOINT` — base URL of the build runtime
- `EXTERNAL_BUILD_AGENT_MODEL_ID` — model identifier expected by the runtime
- `M3TA_LITELLM_BASE_URL` — defaults to `http://localhost:4000/v1`
- `OBSIDIAN_VAULT_PATH` — absolute path to the audit-sink vault
- `SLACK_ALERT_CHANNEL` — channel id or `#channel-name` for run alerts

Optional but recommended:

- `NOTION_TASK_DATABASE_ID` — database id for the task ledger
- `ATTIO_WORKSPACE_ID` — workspace id for CRM-side handoffs

Never commit `.env`. The repo `.gitignore` already excludes it; verify with
`git check-ignore adapters/build-adapter/.env` before any commit.

## MCP server handshake

The adapter expects four MCP servers on the local machine: Notion, Slack,
Attio, Obsidian. The endpoint stubs live in `mcp-config.json`.

Bring them up however your environment prefers (Docker MCP Gateway, native
processes, the `c0achm3ta` profile bootstrap). The adapter does not start
them; it only talks to them.

Verify each is reachable:

```bash
jq -r '.mcpServers | to_entries[] | "\(.key)\t\(.value.url)"' \
  adapters/build-adapter/mcp-config.json \
  | while IFS=$'\t' read -r name url; do
      printf '%-12s %s ' "$name" "$url"
      curl -sS -o /dev/null -w '%{http_code}\n' --max-time 3 "$url" || echo 'unreachable'
    done
```

A `200` or `405` is fine (the latter just means the endpoint refuses `GET`).
Anything else means the server isn't running.

## First-run smoke check

The smoke check exercises the full handoff loop with a trivial hello-world
task. It should complete in under 30 seconds.

```bash
cd adapters/build-adapter
./scripts/build-init.sh --smoke
./scripts/build-plan.sh --task templates/task-scaffold.md --dry-run
./scripts/build-exec.sh --plan /tmp/build-adapter/last-plan.json --dry-run
./scripts/build-doc.sh --session /tmp/build-adapter/last-session.json
./scripts/build-sync.sh --session /tmp/build-adapter/last-session.json
```

Expected outcome:

1. `build-init` prints `READY` and writes `/tmp/build-adapter/session.id`.
2. `build-plan` emits a JSON plan with at least one step.
3. `build-exec --dry-run` reports each step as `would-execute` without
   touching the filesystem.
4. `build-doc` writes a markdown summary to the Obsidian vault.
5. `build-sync` posts the session summary to the configured Slack channel
   and creates a Notion task entry.

If any step fails, read the matching section in `RUNBOOK.md` rather than
patching forward.

## Done

The adapter is bootstrapped. Real tasks go through the same five-step CLI;
`RUNBOOK.md` covers operational use.
