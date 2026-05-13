#!/usr/bin/env bash
# scripts/dev-down.sh — tear down the M3ta-0s 3-service local stack.
# Kills processes bound to ports 8421/5173 and, if present, the tmux session
# spawned by dev-up.sh with M3TA_USE_TMUX=1.
#
# T1 (core/m3ta-os bun dev) doesn't bind a public port by default; if you ran
# it under tmux this script also kills that pane via the session teardown.
# Otherwise stop T1 manually in its terminal.

set -euo pipefail

c_reset=$'\033[0m'
c_grn=$'\033[1;32m'
c_yel=$'\033[1;33m'
c_cyn=$'\033[1;36m'

ok()   { printf "%s ok %s %s\n" "$c_grn" "$c_reset" "$*"; }
warn() { printf "%s !! %s %s\n" "$c_yel" "$c_reset" "$*"; }
info() { printf "%s -- %s %s\n" "$c_cyn" "$c_reset" "$*"; }

for port in 8421 5173; do
  pids="$(lsof -ti ":$port" -sTCP:LISTEN 2>/dev/null || true)"
  if [[ -n "$pids" ]]; then
    info "killing pids on port $port: $pids"
    # shellcheck disable=SC2086
    kill $pids 2>/dev/null || true
    sleep 1
    pids2="$(lsof -ti ":$port" -sTCP:LISTEN 2>/dev/null || true)"
    if [[ -n "$pids2" ]]; then
      warn "port $port still bound, sending SIGKILL"
      # shellcheck disable=SC2086
      kill -9 $pids2 2>/dev/null || true
    fi
    ok "port $port freed"
  else
    ok "port $port already free"
  fi
done

if command -v tmux >/dev/null 2>&1 && tmux has-session -t m3ta-os 2>/dev/null; then
  info "killing tmux session m3ta-os"
  tmux kill-session -t m3ta-os
  ok "tmux session m3ta-os killed"
fi

ok "all services on 8421/5173 stopped"
