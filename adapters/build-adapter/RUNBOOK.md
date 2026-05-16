# Runbook

Day-to-day operations for `adapters/build-adapter/`. Assumes the adapter is
already bootstrapped; see `BOOTSTRAP.md` if not.

## Standard session

A normal task runs through five subcommands. Each one is a thin bash
wrapper; the heavy logic lives in the build runtime and the classifier.

```bash
./scripts/build-init.sh                          # 1. open a session
./scripts/build-plan.sh --task path/to/task.md   # 2. produce a plan
./scripts/build-exec.sh --plan /tmp/build-adapter/last-plan.json
./scripts/build-doc.sh --session /tmp/build-adapter/last-session.json
./scripts/build-sync.sh --session /tmp/build-adapter/last-session.json
```

A session file is written under `/tmp/build-adapter/`. The session id flows
through every step; do not edit it by hand.

### Subcommand reference

- `build-init` — opens a session, verifies MCP servers, writes the session
  id. Flags: `--smoke` (skip MCP checks for the install smoke test).
- `build-plan` — classifies the task, produces a JSON plan with steps and a
  `model_route_hint`. Flags: `--task PATH` (required), `--dry-run`.
- `build-exec` — runs the plan. Flags: `--plan PATH` (required),
  `--dry-run`, `--stop-on-error` (default: true).
- `build-doc` — renders the session summary to markdown in the Obsidian
  vault. Flags: `--session PATH` (required).
- `build-sync` — posts the session summary to Slack and creates/updates a
  Notion task entry. Flags: `--session PATH` (required), `--no-slack`,
  `--no-notion`.

### Output contract recap

Every session result is a JSON object with `session_id`, `status`,
`summary`, `changes[]`, `commands_run[]`, `next_steps[]`, `errors[]`, and
`model_route_hint`. The `RUNBOOK` does not duplicate the schema; it lives
in `PROMPT.md`.

## Monitoring touchpoints

- **Slack alerts** — `build-sync` posts a one-line summary on every
  session, and a full payload on any non-`ok` status.
- **Obsidian vault** — `build-doc` appends a session log under
  `$OBSIDIAN_VAULT_PATH/build-adapter/`, dated and session-keyed.
- **Notion task ledger** — `build-sync` creates a row in the database
  identified by `NOTION_TASK_DATABASE_ID` with status, summary, and a link
  back to the Obsidian log.
- **Local logs** — every script tees its stdout and stderr to
  `/tmp/build-adapter/logs/<session-id>.log` for 7 days.

## Error recovery

A symptom-to-fix matrix for the failures that have actually shown up. Add
rows as new failure modes appear; keep this table dense and source-anchored.

| Symptom                                                | Likely cause                            | Fix                                                                                                                  |
| ------------------------------------------------------ | --------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| `build-init` reports `MCP unreachable: notion`         | Notion MCP server not running           | Start the MCP gateway profile that includes `notion`; re-run `build-init`.                                           |
| `build-plan` exits with `wrong-route`                  | Task verb didn't classify as build      | Inspect `router/task-classifier.ts` rules; either rewrite the task or route through the orchestration layer instead. |
| `build-exec` halts at step N with `missing-resource`   | A file or repo referenced doesn't exist | Stop. Do not substitute. Surface the missing resource to the maintainer and let them choose.                         |
| `build-doc` fails with `EACCES` on the Obsidian path   | Vault path is wrong or read-only        | Re-check `OBSIDIAN_VAULT_PATH`; verify with `test -w "$OBSIDIAN_VAULT_PATH"`.                                        |
| `build-sync` posts to Slack but Notion row not created | `NOTION_TASK_DATABASE_ID` unset         | Set it in `.env`; re-run `build-sync --no-slack` to backfill without double-posting.                                 |
| Session output is empty JSON                           | Runtime crashed before emitting result  | Check `/tmp/build-adapter/logs/<session-id>.log` for the stderr trail.                                               |
| `model_route_hint` always `null`                       | Classifier confidence below threshold   | Raise verbosity in the task description; the classifier needs verb signals.                                          |

## Escalation

If a session fails twice on the same task with the same error code, stop
the loop. Open an issue in `m3ta-empire` with:

- The full session JSON (redact secrets).
- The task input verbatim.
- The relevant slice of `/tmp/build-adapter/logs/<session-id>.log`.
- Any environment delta from a known-good run.

Do not edit the task description and retry blind. The classifier and the
runtime should give the same answer for the same input; if they don't, that
is a bug worth a paper trail.

## Periodic maintenance

- **Weekly** — clear `/tmp/build-adapter/logs/` of files older than 7 days
  (the scripts handle this on init; manual rotation only if disk fills).
- **Monthly** — re-run `BOOTSTRAP.md`'s smoke check to catch silent drift
  in MCP server endpoints or environment.
- **On runtime swap** — re-read `PROMPT.md` end-to-end; the prompt is the
  only contract between the adapter and the runtime.
