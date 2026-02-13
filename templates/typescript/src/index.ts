#!/usr/bin/env node

/**
 * {{SERVER_DESCRIPTION}}
 *
 * MCP Server Entry Point
 * Supports both stdio (local) and HTTP (remote) transports.
 *
 * Usage:
 *   stdio:  node dist/index.js
 *   http:   node dist/index.js --transport http --port 3000
 */

import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { createServer } from "./server/index.js";

// ---------------------------------------------------------------------------
// Transport selection
// ---------------------------------------------------------------------------

async function main(): Promise<void> {
  const args = process.argv.slice(2);
  const transportType = getArg(args, "--transport") ?? "stdio";

  // Create the MCP server with all tools, resources, and prompts registered
  const { server, cleanup } = createServer();

  if (transportType === "stdio") {
    // stdio transport: communicate via stdin/stdout (used by Claude Desktop, etc.)
    const transport = new StdioServerTransport();
    await server.connect(transport);

    // Graceful shutdown
    process.on("SIGINT", async () => {
      await cleanup();
      await server.close();
      process.exit(0);
    });
  } else if (transportType === "http") {
    // HTTP transport: Streamable HTTP for remote/cloud deployments
    const port = parseInt(getArg(args, "--port") ?? "3000", 10);

    // Dynamic import to avoid loading express when using stdio
    const { startHttpTransport } = await import("./server/http-transport.js");
    await startHttpTransport(server, port, cleanup);
  } else {
    // IMPORTANT: Use stderr for logging in MCP servers (stdout is for JSON-RPC)
    console.error(`Unknown transport: ${transportType}`);
    console.error("Supported transports: stdio, http");
    process.exit(1);
  }
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function getArg(args: string[], flag: string): string | undefined {
  const index = args.indexOf(flag);
  return index !== -1 && index + 1 < args.length ? args[index + 1] : undefined;
}

main().catch((error) => {
  console.error("Fatal error:", error);
  process.exit(1);
});
