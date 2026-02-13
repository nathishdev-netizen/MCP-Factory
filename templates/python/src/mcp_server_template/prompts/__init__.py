"""
Prompts Registry

Imports and registers all prompts with the MCP server.
Each prompt lives in its own file — same pattern as tools.
Prompts are user-controlled reusable templates that guide LLM workflows.
"""

from mcp.server.fastmcp import FastMCP

# {{PROMPT_IMPORTS}} — AI factory adds imports dynamically
# from .summarize import register_summarize_prompt
# from .daily_report import register_daily_report_prompt


def register_all_prompts(mcp: FastMCP) -> None:
    """Register all prompts with the server."""

    # {{PROMPT_REGISTRATIONS}} — AI factory adds calls dynamically
    # register_summarize_prompt(mcp)
    # register_daily_report_prompt(mcp)
    pass
