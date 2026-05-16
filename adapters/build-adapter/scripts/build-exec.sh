#!/usr/bin/env bash
# build-exec.sh — execute a build plan against the external build runtime.
#
# Reads a plan JSON written by build-plan, posts it to the runtime endpoint
# named in EXTERNAL_BUILD_AGENT_ENDPOINT, and writes the session result to
# /tmp/build-adapter/last-session.json.
#
# This script does not invent file paths; it only hands the plan over and
# captures the runtime's response. If the runtime is not configured, exit
# non-zero rather than silently degrading.
#
# Flags:
#   --plan PATH      required; plan JSON produced by build-plan.sh
#   --dry-run        report each step as would-execute; no runtime call
#   --stop-on-error  default 1; set to 0 to keep going past failed steps
#   --help           print this header and exit

set -euo pipefail

PLAN=""
DRY_RUN=0
STOP_ON_ERROR=1
while [ "$#" -gt 0 ]; do
  case "$1" in
    --plan) PLAN="$2"; shift 2 ;;
    --dry-run) DRY_RUN=1; shift ;;
    --stop-on-error) STOP_ON_ERROR="$2"; shift 2 ;;
    --help|-h) sed -n '2,18p' "$0"; exit 0 ;;
    *) printf 'unknown argument: %s\n' "$1" >&2; exit 64 ;;
  esac
done

if [ -z "${PLAN}" ]; then
  printf 'missing required flag: --plan\n' >&2
  exit 64
fi
if [ ! -f "${PLAN}" ]; then
  printf 'plan file not found: %s\n' "${PLAN}" >&2
  exit 66
fi

ADAPTER_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SCRATCH_DIR="${BUILD_ADAPTER_SCRATCH:-/tmp/build-adapter}"
SESSION_OUT="${SCRATCH_DIR}/last-session.json"
mkdir -p "${SCRATCH_DIR}"

if [ -f "${ADAPTER_DIR}/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  . "${ADAPTER_DIR}/.env"
  set +a
fi

SESSION_ID=$(jq -r '.session_id' "${PLAN}")
ROUTE=$(jq -r '.classification.route' "${PLAN}")

# Refuse non-build routes loudly.
case "${ROUTE}" in
  build|build-with-review) ;;
  *)
    jq -n --arg sid "${SESSION_ID}" --arg route "${ROUTE}" \
      '{session_id:$sid,status:"wrong-route",summary:"task did not classify as build",changes:[],commands_run:[],next_steps:[],errors:[{code:"wrong-route",detail:$route}],model_route_hint:null}' \
      > "${SESSION_OUT}"
    printf 'wrong-route: %s\n' "${ROUTE}" >&2
    exit 65
    ;;
esac

if [ "${DRY_RUN}" -eq 1 ]; then
  jq --arg sid "${SESSION_ID}" \
    '{session_id:$sid,status:"ok",summary:"dry-run; no steps executed",changes:[],commands_run:[],next_steps:["wire a runtime to exercise build-exec"],errors:[],model_route_hint:(.classification.modelRouteHint)}' \
    "${PLAN}" > "${SESSION_OUT}"
  printf 'dry-run complete: %s\n' "${SESSION_OUT}"
  exit 0
fi

# Real-runtime path. Requires EXTERNAL_BUILD_AGENT_ENDPOINT and
# EXTERNAL_BUILD_AGENT_API_KEY to be set.
if [ -z "${EXTERNAL_BUILD_AGENT_ENDPOINT:-}" ] || [ -z "${EXTERNAL_BUILD_AGENT_API_KEY:-}" ]; then
  printf 'runtime not configured; set EXTERNAL_BUILD_AGENT_ENDPOINT and EXTERNAL_BUILD_AGENT_API_KEY or use --dry-run\n' >&2
  exit 78
fi

LOG="${SCRATCH_DIR}/logs/${SESSION_ID}.log"
RESPONSE=$(
  curl -sS -X POST \
    -H "Authorization: Bearer ${EXTERNAL_BUILD_AGENT_API_KEY}" \
    -H 'Content-Type: application/json' \
    --data @"${PLAN}" \
    --max-time 600 \
    "${EXTERNAL_BUILD_AGENT_ENDPOINT}/execute" 2>>"${LOG}" \
  || echo '{}'
)

if ! printf '%s' "${RESPONSE}" | jq -e '.session_id' >/dev/null 2>&1; then
  jq -n --arg sid "${SESSION_ID}" --arg log "${LOG}" \
    '{session_id:$sid,status:"failed",summary:"runtime returned no parseable session",changes:[],commands_run:[],next_steps:["inspect log"],errors:[{code:"empty-response",detail:$log}],model_route_hint:null}' \
    > "${SESSION_OUT}"
  if [ "${STOP_ON_ERROR}" -eq 1 ]; then exit 70; fi
  exit 0
fi

printf '%s' "${RESPONSE}" > "${SESSION_OUT}"
printf 'session result written: %s\n' "${SESSION_OUT}"
