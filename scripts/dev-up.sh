#!/usr/bin/env bash
# scripts/dev-up.sh — bring up the M3ta-0s 3-service local stack.
#
# Services:
#   T1  core/m3ta-os          (Bun)
#   T2  integrations/lyzr     (uvicorn, port 8421, needs LYZR_AGENT_* in .env)
#   T3  apps/qu3bii-dashboard (Bun, port 5173)
#
# Pre-flight: verifies bun + uvicorn are on PATH, .env has LYZR_AGENT_* vars,
# ports 8421/5173 are free. Then either spawns a tmux session (if tmux is
# present and M3TA_USE_TMUX=1) or prints the three commands for you to paste
# into 3 terminals.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

c_reset=$'\033[0m'
c_red=$'\033[1;31m'
c_grn=$'\033[1;32m'
c_yel=$'\033[1;33m'
c_cyn=$'\033[1;36m'

die()  { printf "%sFAIL%s %s\n" "$c_red" "$c_reset" "$*" >&2; exit 1; }
ok()   { printf "%s ok %s %s\n" "$c_grn" "$c_reset" "$*"; }
warn() { printf "%s !! %s %s\n" "$c_yel" "$c_reset" "$*"; }
info() { printf "%s -- %s %s\n" "$c_cyn" "$c_reset" "$*"; }

info "Pre-flight checks..."

command -v bun     >/dev/null 2>&1 || die "bun not on PATH (install: curl -fsSL https://bun.sh/install | bash)"
command -v uvicorn >/dev/null 2>&1 || die "uvicorn not on PATH (install: pipx install uvicorn or pip install 'uvicorn[standard]')"
ok "bun and uvicorn present"

ENV_FILE="$REPO_ROOT/core/m3ta-os/.env"
if [[ ! -f "$ENV_FILE" ]]; then
  die ".env missing at core/m3ta-os/.env — copy .env.example and fill in LYZR_AGENT_* vars"
fi
if ! grep -qE '^LYZR_AGENT_[A-Z0-9_]+=' "$ENV_FILE"; then
  die "no LYZR_AGENT_* var found in core/m3ta-os/.env (the bridge needs at least one)"
fi
ok ".env present with LYZR_AGENT_* vars"

for port in 8421 5173; do
  if lsof -i ":$port" -sTCP:LISTEN >/dev/null 2>&1; then
    die "port $port already in use — run scripts/dev-down.sh first"
  fi
done
ok "ports 8421 and 5173 free"

# tmux fast path
if command -v tmux >/dev/null 2>&1 && [[ "${M3TA_USE_TMUX:-0}" == "1" ]]; then
  SESS="m3ta-os"
  if tmux has-session -t "$SESS" 2>/dev/null; then
    warn "tmux session $SESS already exists — attaching"
    exec tmux attach -t "$SESS"
  fi
  info "Spawning tmux session $SESS with 3 panes..."
  tmux new-session  -d -s "$SESS" -n stack -c "$REPO_ROOT/core/m3ta-os"          "bun run dev"
  tmux split-window -h -t "$SESS:stack"    -c "$REPO_ROOT/integrations/lyzr"     "uvicorn n8n_webhook:app --port 8421"
  tmux split-window -v -t "$SESS:stack"    -c "$REPO_ROOT/apps/qu3bii-dashboard" "bun run dev"
  tmux select-layout -t "$SESS:stack" tiled
  ok "tmux session ready"
  printf "%sopen%s   http://localhost:5173 then click Brain Personas\n" "$c_cyn" "$c_reset"
  printf "%sattach%s tmux attach -t %s\n" "$c_cyn" "$c_reset" "$SESS"
  printf "%sdown%s   scripts/dev-down.sh\n" "$c_cyn" "$c_reset"
  exit 0
fi

# Manual path: print copy-paste commands
cat <<EOF

${c_grn}Pre-flight passed.${c_reset} Paste each line into its own terminal:

  ${c_cyn}T1${c_reset}  cd $REPO_ROOT/core/m3ta-os          && bun run dev
  ${c_cyn}T2${c_reset}  cd $REPO_ROOT/integrations/lyzr     && uvicorn n8n_webhook:app --port 8421
  ${c_cyn}T3${c_reset}  cd $REPO_ROOT/apps/qu3bii-dashboard && bun run dev

Then open http://localhost:5173 and click Brain Personas.

${c_yel}Tip${c_reset}: M3TA_USE_TMUX=1 scripts/dev-up.sh spawns a tmux session with all 3 panes.
EOF
