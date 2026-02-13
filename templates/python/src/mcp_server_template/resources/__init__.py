"""
Resources Registry

Imports and registers all resources with the MCP server.
Each resource lives in its own file — same pattern as tools.
Resources are READ-ONLY data endpoints accessed via URI templates.
"""

from mcp.server.fastmcp import FastMCP

# {{RESOURCE_IMPORTS}} — AI factory adds imports dynamically
# from .server_status import register_server_status_resource
# from .todo_list import register_todo_list_resource


def register_all_resources(mcp: FastMCP) -> None:
    """Register all resources with the server."""

    # {{RESOURCE_REGISTRATIONS}} — AI factory adds calls dynamically
    # register_server_status_resource(mcp)
    # register_todo_list_resource(mcp)
    pass
