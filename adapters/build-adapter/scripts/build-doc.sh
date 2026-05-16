#!/usr/bin/env bash
# build-doc.sh — render a session result to markdown in the Obsidian vault.
#
# Reads a session JSON (the output contract from PROMPT.md) and writes a
# dated, session-keyed markdown file under
# $OBSIDIAN_VAULT_PATH/build-adapter/. Idempotent; rerunning overwrites.
#
# Flags:
#   --session PATH   required; session JSON produced by build-exec.sh
#   --help           print this header and exit

set -euo pipefail

SESSION=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --session) SESSION="$2"; shift 2 ;;
    --help|-h) sed -n '2,11p' "$0"; exit 0 ;;
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

if [ -z "${OBSIDIAN_VAULT_PATH:-}" ]; then
  printf 'OBSIDIAN_VAULT_PATH not set\n' >&2
  exit 78
fi
if [ ! -w "${OBSIDIAN_VAULT_PATH}" ]; then
  printf 'OBSIDIAN_VAULT_PATH not writable: %s\n' "${OBSIDIAN_VAULT_PATH}" >&2
  exit 73
fi

VAULT_SUBDIR="${OBSIDIAN_VAULT_PATH%/}/build-adapter"
mkdir -p "${VAULT_SUBDIR}"

SESSION_ID=$(jq -r '.session_id' "${SESSION}")
STATUS=$(jq -r '.status' "${SESSION}")
SUMMARY=$(jq -r '.summary' "${SESSION}")
DATE=$(date -u +%Y-%m-%d)
OUT="${VAULT_SUBDIR}/${DATE}-${SESSION_ID}.md"

{
  printf '# Build session %s\n\n' "${SESSION_ID}"
  printf '- Status: %s\n' "${STATUS}"
  printf '- Date (UTC): %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  printf '\n## Summary\n\n%s\n' "${SUMMARY}"

  printf '\n## Changes\n\n'
  jq -r '.changes[]? | "- " + .action + " " + .path + " (" + (.bytes|tostring) + " bytes)"' "${SESSION}"

  printf '\n## Commands run\n\n'
  jq -r '.commands_run[]? | "- `" + . + "`"' "${SESSION}"

  printf '\n## Next steps\n\n'
  jq -r '.next_steps[]? | "- " + .' "${SESSION}"

  ERR_COUNT=$(jq -r '.errors | length' "${SESSION}")
  if [ "${ERR_COUNT}" -gt 0 ]; then
    printf '\n## Errors\n\n'
    jq -r '.errors[] | "- **" + .code + "**: " + .detail' "${SESSION}"
  fi

  HINT=$(jq -r '.model_route_hint // "null"' "${SESSION}")
  printf '\n## Model route hint\n\n`%s`\n' "${HINT}"
} > "${OUT}"

printf 'doc written: %s\n' "${OUT}"
