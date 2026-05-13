#!/usr/bin/env bash
# route-health.sh — smoke-test M3ta-0s LiteLLM routes and emit JSON.
#
# Installed via com.m3taos.route-health LaunchAgent on a 30-minute interval.
# Alerts only when the set of failing routes CHANGES between two consecutive
# runs (PONG -> error transitions) to avoid alert fatigue.
set -uo pipefail

PROXY="${M3TAOS_PROXY:-http://localhost:4000/v1}"
ROUTES=(m3ta-default m3ta-code m3ta-reasoning m3ta-fast m3ta-heavy m3ta-oss m3ta-embed)
OUT_DIR="$HOME/.m3ta-os/route-health"
mkdir -p "$OUT_DIR"

DATE="$(date +%Y-%m-%d)"
TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
OUT_FILE="$OUT_DIR/$DATE.json"
LAST_FILE="$OUT_DIR/last.json"

declare -a results=()
for r in "${ROUTES[@]}"; do
  if [[ "$r" == "m3ta-embed" ]]; then
    out=$(curl -sS -m 15 \
      -H 'Authorization: Bearer anything' \
      -H 'Content-Type: application/json' \
      -d "{\"model\":\"$r\",\"input\":\"PING\"}" \
      "$PROXY/embeddings" 2>/dev/null \
      | jq -r '.data[0].embedding | length // .error.message // "no-data"' 2>/dev/null)
    if [[ "$out" =~ ^[0-9]+$ ]]; then
      state="ok"; detail="embedding_dim=$out"
    else
      state="error"; detail="${out:-no-data}"
    fi
  else
    out=$(curl -sS -m 30 \
      -H 'Authorization: Bearer anything' \
      -H 'Content-Type: application/json' \
      -d "{\"model\":\"$r\",\"messages\":[{\"role\":\"user\",\"content\":\"PING\"}],\"max_tokens\":8}" \
      "$PROXY/chat/completions" 2>/dev/null \
      | jq -r '.choices[0].message.content // .error.message // "no-content"' 2>/dev/null \
      | tr '\n' ' ' | head -c 80)
    if [[ -z "$out" || "$out" == "no-content" || "$out" =~ [Ee]rror ]]; then
      state="error"; detail="${out:-empty}"
    else
      state="ok"; detail="$out"
    fi
  fi
  results+=("{\"route\":\"$r\",\"state\":\"$state\",\"detail\":$(jq -Rs . <<<"$detail")}")
done

joined=$(IFS=,; echo "${results[*]}")
report="{\"timestamp\":\"$TS\",\"routes\":[$joined]}"
echo "$report" | jq . > "$OUT_FILE"

# Transition detection — only iMessage when the set of failing routes flips.
if [[ -f "$LAST_FILE" ]]; then
  prev_errors=$(jq -r '.routes[] | select(.state=="error") | .route' "$LAST_FILE" 2>/dev/null | sort -u | paste -sd, -)
  curr_errors=$(jq -r '.routes[] | select(.state=="error") | .route' "$OUT_FILE" 2>/dev/null | sort -u | paste -sd, -)
  if [[ "$prev_errors" != "$curr_errors" ]]; then
    summary="M3ta-0s route-health change at $TS: prev=[$prev_errors] now=[$curr_errors]"
    if command -v osascript >/dev/null 2>&1 && [[ -n "${M3TAOS_IMESSAGE_TO:-}" ]]; then
      osascript -e "tell application \"Messages\" to send \"$summary\" to buddy \"$M3TAOS_IMESSAGE_TO\"" 2>/dev/null || true
    fi
  fi
fi

cp "$OUT_FILE" "$LAST_FILE"
exit 0
