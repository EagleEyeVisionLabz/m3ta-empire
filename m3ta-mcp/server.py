"""m3ta-mcp — M3ta-0s tool server skeleton.

First commit: hello-world tool registration to validate the
Hermes Agent <-> MCP runtime path. Real tool surface lands incrementally.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("m3ta-mcp")


@mcp.tool()
def hello(name: str = "M3ta") -> str:
    """Smoke-test tool. Returns a greeting confirming the MCP wiring is alive."""
    return f"hello, {name} — m3ta-mcp is alive"


if __name__ == "__main__":
    # FastMCP.run() defaults to stdio transport, which is what Hermes expects.
    mcp.run()
