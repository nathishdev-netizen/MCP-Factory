"""
Tools Registry

Imports and registers all tools with the MCP server.
AI Factory adds import + registration for each generated tool.
"""

from mcp.server.fastmcp import FastMCP

# {{TOOL_IMPORTS}} — AI factory adds imports dynamically
# from .search_hotels import register_search_hotels_tool
# from .book_hotel import register_book_hotel_tool


def register_all_tools(mcp: FastMCP) -> None:
    """Register all tools with the server."""

    # {{TOOL_REGISTRATIONS}} — AI factory adds calls dynamically
    # register_search_hotels_tool(mcp)
    # register_book_hotel_tool(mcp)
    pass
