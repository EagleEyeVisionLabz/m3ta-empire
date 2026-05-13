# Runbook: Route-Health Daemon

Recurring health check for the seven M3ta-0s LiteLLM routes. Runs every
30 minutes via a LaunchAgent, writes a JSON report per day to
`~/.m3ta-os/route-health/`, and only sends an iMessage when the set of
failing routes **changes** between consecutive runs — avoids alert fatigue.

## Install

```bash
# 1. Drop the script into the M3ta-0s scripts dir.
mkdir -p ~/.m3ta-os/scripts
cp scripts/route-health.sh ~/.m3ta-os/scripts/route-health.sh
chmod +x ~/.m3ta-os/scripts/route-health.sh

# 2. Install the LaunchAgent.
mkdir -p ~/Library/LaunchAgents
cp launchagents/com.m3taos.route-health.plist \
   ~/Library/LaunchAgents/com.m3taos.route-health.plist

# 3. (Optional) Set the iMessage destination.
echo 'export M3TAOS_IMESSAGE_TO="+1XXXXXXXXXX"' >> ~/.m3ta-os/config/.env

# 4. Load and kick.
launchctl bootstrap "gui/$UID" \
  ~/Library/LaunchAgents/com.m3taos.route-health.plist
launchctl kickstart -k "gui/$UID/com.m3taos.route-health"
```

## Verify

```bash
launchctl print "gui/$UID/com.m3taos.route-health" \
  | grep -E "state|next run|last exit"
ls -la ~/.m3ta-os/route-health/
jq . ~/.m3ta-os/route-health/last.json
```

A healthy report looks like:

```json
{
  "timestamp": "2026-05-13T15:00:00Z",
  "routes": [
    { "route": "m3ta-default", "state": "ok", "detail": "PONG" },
    { "route": "m3ta-embed",   "state": "ok", "detail": "embedding_dim=768" }
  ]
}
```

## Tune

- **Interval:** edit `StartInterval` in the plist (seconds; default 1800).
- **Alert destination:** set `M3TAOS_IMESSAGE_TO` in `~/.m3ta-os/config/.env`. Unset to disable alerts entirely.
- **Proxy URL:** set `M3TAOS_PROXY` in the env file if you're not on the default `http://localhost:4000/v1`.

## Uninstall

```bash
launchctl bootout "gui/$UID" \
  ~/Library/LaunchAgents/com.m3taos.route-health.plist
rm ~/Library/LaunchAgents/com.m3taos.route-health.plist
rm ~/.m3ta-os/scripts/route-health.sh
```

## Why transitions, not levels

The model-watch cron already sends a daily digest of upstream model
drift. A second daily reminder that the same broken route is still
broken would just train you to ignore the channel. So this daemon
only fires when the set of failing routes **changes** between two
consecutive runs.
