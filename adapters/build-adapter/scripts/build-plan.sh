#!/usr/bin/env bash
# build-plan.sh — classify a task and emit a plan JSON.
#
# Reads a task description from a markdown file, runs the verb classifier,
# and writes a plan to /tmp/build-adapter/last-plan.json. Does not call
# the external build runtime; that is build-exec's job.
#
# Flags:
#   --task PATH    required; markdown file describing the task
#   --dry-run      classify only; do not write a plan file
#   --help         print this header and exit

set -euo pipefail

TASK=""
DRY_RUN=0
while [ "$#" -gt 0 ]; do
  case "$1" in
    --task) TASK="$2"; shift 2 ;;
    --dry-run) DRY_RUN=1; shift ;;
    --help|-h) sed -n '2,12p' "$0"; exit 0 ;;
    *) printf 'unknown argument: %s\n' "$1" >&2; exit 64 ;;
  esac
done

if [ -z "${TASK}" ]; then
  printf 'missing required flag: --task\n' >&2
  exit 64
fi
if [ ! -f "${TASK}" ]; then
  printf 'task file not found: %s\n' "${TASK}" >&2
  exit 66
fi

ADAPTER_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SCRATCH_DIR="${BUILD_ADAPTER_SCRATCH:-/tmp/build-adapter}"
mkdir -p "${SCRATCH_DIR}"

CLASSIFIER="${ADAPTER_DIR}/router/task-classifier.ts"
if [ ! -f "${CLASSIFIER}" ]; then
  printf 'classifier missing at %s\n' "${CLASSIFIER}" >&2
  exit 66
fi

# Pass the first non-blank line of the task file to the classifier. The
# verb-based router only needs the leading verb; the runtime gets the
# full body separately.
FIRST_LINE=$(grep -m1 -E '\S' "${TASK}" | sed 's/^#\+\s*//')
CLASSIFICATION=$(
  if command -v bun >/dev/null 2>&1; then
    bun run "${CLASSIFIER}" -- "${FIRST_LINE}"
  else
    printf 'bun is required to run the classifier\n' >&2
    exit 69
  fi
)

SESSION_ID=$(cat "${SCRATCH_DIR}/session.id" 2>/dev/null || echo 'unbound')
PLAN_PATH="${SCRATCH_DIR}/last-plan.json"

PLAN=$(
  jq -n \
    --arg session "${SESSION_ID}" \
    --arg task_path "${TASK}" \
    --arg first_line "${FIRST_LINE}" \
    --argjson classification "${CLASSIFICATION}" \
    '{
      session_id: $session,
      task_path: $task_path,
      task_first_line: $first_line,
      classification: $classification,
      steps: [],
      created_at: (now | todate)
    }'
)

if [ "${DRY_RUN}" -eq 1 ]; then
  printf '%s\n' "${PLAN}"
  exit 0
fi

printf '%s\n' "${PLAN}" > "${PLAN_PATH}"
printf 'plan written: %s\n' "${PLAN_PATH}"
