# m3ta-mcp

Tool server for the M3ta-0s agent runtime. Exposes the M3ta-0s tool surface to Hermes Agent — and any other MCP client — via the Model Context Protocol.

**Status: scaffold.** First commit registers a single `hello` tool to validate the Hermes ↔ MCP wiring; the real tool surface lands incrementally.

## Reference architecture

- **Runtime:** Hermes Agent kernel on macOS.
- **Transport:** MCP over stdio for local invocation; SSE for remote callers later.
- **Language:** Python first (this scaffold). Elixir via [`hermes_mcp`](https://github.com/NousResearch/hermes_mcp) is the planned production target — both speak the same protocol so MCP clients are portable across them.

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python server.py
```

The server speaks stdio MCP by default; point any MCP-aware client at it.

## Smoke-test from Hermes

Add this entry to `~/.hermes/config.yaml` under `mcp.servers`:

```yaml
m3ta-mcp:
  command: python
  args: ["<absolute-path-to>/m3ta-mcp/server.py"]
```

Then ask Hermes to call the `hello` tool — a non-empty response confirms the wiring.

## Roadmap

- [ ] Register a real tool that hits the LiteLLM proxy on `localhost:4000`.
- [ ] Add the Apple Bridge tools (Notes, OmniFocus, Things3, Reminders, Calendar) as MCP tools.
- [ ] Migrate the server to Elixir via `hermes_mcp` once the Python surface stabilizes.
