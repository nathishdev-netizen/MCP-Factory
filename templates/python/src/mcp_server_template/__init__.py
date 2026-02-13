"""
{{SERVER_DESCRIPTION}}

MCP Server — Entry point.
Supports stdio (default) and HTTP transports.

Usage:
  stdio:  mcp-server-{{SERVER_NAME}}
  http:   mcp-server-{{SERVER_NAME}} --transport http --port 3000
  debug:  mcp-server-{{SERVER_NAME}} -vv
"""

import click
import asyncio
import logging

from .server import create_server


@click.command()
@click.option(
    "--transport",
    type=click.Choice(["stdio", "http"]),
    default="stdio",
    help="Transport type (stdio for local, http for remote)",
)
@click.option(
    "--port",
    type=int,
    default=3000,
    help="Port for HTTP transport",
)
@click.option(
    "-v", "--verbose",
    count=True,
    help="Increase verbosity (-v = INFO, -vv = DEBUG)",
)
def main(transport: str, port: int, verbose: int) -> None:
    """{{SERVER_DESCRIPTION}} — MCP Server"""

    # Configure logging (MUST use stderr, never stdout!)
    log_level = {0: logging.WARNING, 1: logging.INFO}.get(verbose, logging.DEBUG)
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
        # Critical: log to stderr, NOT stdout
        handlers=[logging.StreamHandler()],
    )

    mcp = create_server(port=port if transport == "http" else None)

    if transport == "stdio":
        mcp.run(transport="stdio")
    elif transport == "http":
        mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
