#!/usr/bin/env bash
# build-init.sh — open a build-adapter session.
#
# Verifies the local environment, optionally pings each MCP server, and
# writes a fresh session id to the scratch dir. Other scripts in this
# folder expect the scratch dir to exist.
#
# Flags:
#   --smoke   skip MCP reachability checks (used by the install smoke test)
#   --help    print this header and exit

set -euo pipefail

SMOKE=0
for arg in "$@"; do
  case "$arg" in
    --smoke) SMOKE=1 ;;
    --help|-h)
      sed -n '2,12p' "$0"
      exit 0
      ;;
    *)
      printf 'unknown argument: %s\n' "$arg" >&2
      exit 64
      ;;
  esac
done

ADAPTER_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SCRATCH_DIR="${BUILD_ADAPTER_SCRATCH:-/tmp/build-adapter}"
LOG_DIR="${SCRATCH_DIR}/logs"
mkdir -p "${SCRATCH_DIR}" "${LOG_DIR}"

# Rotate logs older than 7 days.
find "${LOG_DIR}" -type f -mtime +7 -delete 2>/dev/null || true

# Load .env if present, but never echo the values.
if [ -f "${ADAPTER_DIR}/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  . "${ADAPTER_DIR}/.env"
  set +a
fi

REQUIRED_VARS=(
  EXTERNAL_BUILD_AGENT_ENDPOINT
  M3TA_LITELLM_BASE_URL
  OBSIDIAN_VAULT_PATH
)
MISSING=()
for v in "${REQUIRED_VARS[@]}"; do
  if [ -z "${!v:-}" ]; then MISSING+=("$v"); fi
done
if [ "${#MISSING[@]}" -gt 0 ]; then
  printf 'missing required env vars: %s\n' "${MISSING[*]}" >&2
  exit 78
fi

SESSION_ID="bld-$(date -u +%Y%m%dT%H%M%SZ)-$RANDOM"
echo "${SESSION_ID}" > "${SCRATCH_DIR}/session.id"

if [ "${SMOKE}" -ne 1 ]; then
  CONFIG="${ADAPTER_DIR}/mcp-config.json"
  if [ ! -f "${CONFIG}" ]; then
    printf 'mcp-config.json missing at %s\n' "${CONFIG}" >&2
    exit 66
  fi
  if ! command -v jq >/dev/null 2>&1; then
    printf 'jq is required on PATH\n' >&2
    exit 69
  fi
  if ! command -v curl >/dev/null 2>&1; then
    printf 'curl is required on PATH\n' >&2
    exit 69
  fi

  jq -r '.mcpServers | to_entries[] | "\(.key)\t\(.value.url)"' "${CONFIG}" \
    | while IFS=$'\t' read -r name url; do
        code=$(curl -sS -o /dev/null -w '%{http_code}' --max-time 3 "${url}" || echo '000')
        case "${code}" in
          2*|4*) printf 'mcp %-10s ok (%s)\n' "${name}" "${code}" ;;
          *)     printf 'mcp %-10s UNREACHABLE (%s)\n' "${name}" "${code}" >&2 ;;
        esac
      done
fi

printf 'session %s\n' "${SESSION_ID}"
printf 'READY\n'
