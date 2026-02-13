"""
Shared in-memory data store.

All tools and resources should import from this module to share state.
This ensures every tool operates on the same data instead of creating
isolated module-level variables.

Usage in a tool file:
    from ..utils.store import store

    def register_my_tool(mcp: FastMCP):
        @mcp.tool()
        async def my_tool(key: str) -> str:
            store[key] = {"example": True}
            return json.dumps(store[key])
"""

from __future__ import annotations

# Single shared dict — all tools and resources read/write here.
# Keys and value shapes are determined by the generated code.
store: dict[str, dict] = {}
