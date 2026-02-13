"""
Server Factory

Creates the FastMCP server and registers all tools, resources, and prompts.
FastMCP is the high-level Python API — much simpler than the low-level SDK.

Key difference from TypeScript:
- TypeScript uses server.registerTool() with Zod schemas
- Python uses @mcp.tool() decorators with type hints + Pydantic models
- FastMCP auto-generates JSON Schema from Python type annotations
"""

import logging
from mcp.server.fastmcp import FastMCP

from .tools import register_all_tools
from .resources import register_all_resources
from .prompts import register_all_prompts

logger = logging.getLogger(__name__)


def create_server(port: int | None = None) -> FastMCP:
    """Create and configure the MCP server."""

    kwargs: dict = {
        "name": "{{SERVER_NAME}}",
        # Instructions help the LLM understand what this server does
        "instructions": (
            "{{SERVER_INSTRUCTIONS}}"
            # Example: "This server provides hotel booking tools. "
            # "Use search_hotels to find availability, then book_hotel to make a reservation."
        ),
    }
    if port is not None:
        kwargs["port"] = port

    mcp = FastMCP(**kwargs)

    # Register all capabilities
    register_all_tools(mcp)
    register_all_resources(mcp)
    register_all_prompts(mcp)

    logger.info("Server initialized: %s", mcp.name)

    return mcp
