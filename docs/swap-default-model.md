# Runbook: Swap the M3ta-0s Global Default Model

Change which backend resolves to the `m3ta-default` route in
`~/.m3ta-os/config/litellm-copilot.yaml` — the single knob that all
M3ta-0s clients pick up as their global default.

## When to use this

You want to globally swap the default backend without touching every
downstream tool config. This is the only knob — OpenHands, Aider, and
Hermes intentionally keep their own pinned backends and do **not** follow
`m3ta-default`.

## Pre-flight

1. Confirm the candidate backend is reachable.
   - For an Ollama backend: `ollama list`
   - For a cloud backend: confirm the provider key is set in
     `~/.m3ta-os/config/.env`.
2. Snapshot the current YAML so rollback is one command:
   ```bash
   cp ~/.m3ta-os/config/litellm-copilot.yaml \
      ~/.m3ta-os/config/litellm-copilot.yaml.bak-$(date +%Y%m%d-%H%M%S)
   ```
3. Confirm the proxy listener is up:
   ```bash
   lsof -iTCP:4000 -sTCP:LISTEN
   ```

## Edit

Open `~/.m3ta-os/config/litellm-copilot.yaml` and find the `m3ta-default`
block. Update **only** the `litellm_params.model` field. Leave
`model_name: m3ta-default` untouched so every downstream client keeps
working.

```yaml
- model_name: m3ta-default
  litellm_params:
    model: <provider/backend:tag>     # the new backend reference
    api_base: <if-applicable>
    # api_key: env interpolation; never literal
```

## Reload

```bash
launchctl kickstart -k gui/$UID/com.m3taos.litellm-proxy
```

Wait a few seconds for the proxy to bounce, then confirm the listener:

```bash
nc -z localhost 4000 && echo "proxy listening"
```

## Smoke-test

```bash
curl -sS -m 10 \
  -H 'Authorization: Bearer anything' \
  -H 'Content-Type: application/json' \
  -d '{"model":"m3ta-default","messages":[{"role":"user","content":"PING"}],"max_tokens":8}' \
  http://localhost:4000/v1/chat/completions \
  | jq -r '.choices[0].message.content // .error.message'
```

Expect a short reply (`PONG` or similar). If you see an `.error.message`,
the new backend is misconfigured — roll back.

## Rollback

```bash
ls -t ~/.m3ta-os/config/litellm-copilot.yaml.bak-* | head -1 \
  | xargs -I{} cp {} ~/.m3ta-os/config/litellm-copilot.yaml
launchctl kickstart -k gui/$UID/com.m3taos.litellm-proxy
```

## Notes

- `m3ta-default` is the **only** default that propagates globally.
  Per-tool routes (`m3ta-code`, `m3ta-reasoning`, `m3ta-heavy`,
  `m3ta-oss`, `m3ta-embed`, `m3ta-fast`) are independent and edited the
  same way.
- OpenHands, Aider, and Hermes have their own pinned backends — update
  those tools' configs directly if you want to change them.
- The model-watch cron (07:00 daily) only **notifies** about upstream
  digest drift; it does not auto-pull and will not refill disk.
- For full route inventory and on-demand watch runs, see the M3ta-0s
  project doc.
