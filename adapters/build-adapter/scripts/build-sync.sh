#!/usr/bin/env bash
# build-sync.sh — push a session summary to Slack and Notion.
#
# Slack: one-line summary on every session, full payload when status != ok.
# Notion: create or update a task row in NOTION_TASK_DATABASE_ID.
# Either sink can be skipped individually.
#
# Flags:
#   --session PATH   required; session JSON produced by build-exec.sh
#   --no-slack       skip the Slack post
#   --no-notion      skip the Notion write
#   --help           print this header and exit

set -euo pipefail

SESSION=""
SKIP_SLACK=0
SKIP_NOTION=0
while [ "$#" -gt 0 ]; do
  case "$1" in
    --session) SESSION="$2"; shift 2 ;;
    --no-slack) SKIP_SLACK=1; shift ;;
    --no-notion) SKIP_NOTION=1; shift ;;
    --help|-h) sed -n '2,13p' "$0"; exit 0 ;;
    *) printf 'unknown argument: %s\n' "$1" >&2; exit 64 ;;
  esac
done

if [ -z "${SESSION}" ]; then
  printf 'missing required flag: --session\n' >&2
  exit 64
fi
if [ ! -f "${SESSION}" ]; then
  printf 'session file not found: %s\n' "${SESSION}" >&2
  exit 66
fi

ADAPTER_DIR="$(cd "$(dirname "$0")/.." && pwd)"
if [ -f "${ADAPTER_DIR}/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  . "${ADAPTER_DIR}/.env"
  set +a
fi

SESSION_ID=$(jq -r '.session_id' "${SESSION}")
STATUS=$(jq -r '.status' "${SESSION}")
SUMMARY=$(jq -r '.summary' "${SESSION}")

# --- Slack ------------------------------------------------------------------
if [ "${SKIP_SLACK}" -eq 0 ]; then
  if [ -z "${SLACK_BOT_TOKEN:-}" ] || [ -z "${SLACK_ALERT_CHANNEL:-}" ]; then
    printf 'slack: skipped (SLACK_BOT_TOKEN or SLACK_ALERT_CHANNEL unset)\n' >&2
  else
    LINE="build-adapter ${SESSION_ID} :: ${STATUS} :: ${SUMMARY}"
    PAYLOAD=$(jq -n --arg c "${SLACK_ALERT_CHANNEL}" --arg t "${LINE}" \
      '{channel:$c, text:$t}')
    curl -sS -X POST \
      -H "Authorization: Bearer ${SLACK_BOT_TOKEN}" \
      -H 'Content-Type: application/json; charset=utf-8' \
      --data "${PAYLOAD}" \
      --max-time 10 \
      https://slack.com/api/chat.postMessage >/dev/null
    printf 'slack: posted to %s\n' "${SLACK_ALERT_CHANNEL}"
  fi
fi

# --- Notion -----------------------------------------------------------------
if [ "${SKIP_NOTION}" -eq 0 ]; then
  if [ -z "${NOTION_API_KEY:-}" ] || [ -z "${NOTION_TASK_DATABASE_ID:-}" ]; then
    printf 'notion: skipped (NOTION_API_KEY or NOTION_TASK_DATABASE_ID unset)\n' >&2
  else
    BODY=$(jq -n \
      --arg db "${NOTION_TASK_DATABASE_ID}" \
      --arg sid "${SESSION_ID}" \
      --arg status "${STATUS}" \
      --arg summary "${SUMMARY}" \
      '{
        parent: { database_id: $db },
        properties: {
          "Session": { title: [{ text: { content: $sid } }] },
          "Status":  { select: { name: $status } },
          "Summary": { rich_text: [{ text: { content: $summary } }] }
        }
      }')
    curl -sS -X POST \
      -H "Authorization: Bearer ${NOTION_API_KEY}" \
      -H 'Notion-Version: 2022-06-28' \
      -H 'Content-Type: application/json' \
      --data "${BODY}" \
      --max-time 10 \
      https://api.notion.com/v1/pages >/dev/null
    printf 'notion: row created in %s\n' "${NOTION_TASK_DATABASE_ID}"
  fi
fi
