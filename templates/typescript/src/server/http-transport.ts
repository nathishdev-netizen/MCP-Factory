/**
 * HTTP Transport (Streamable HTTP)
 *
 * For remote/cloud deployments. Follows the MCP 2025-11-25 spec:
 * - Single endpoint supporting POST (messages) and GET (SSE stream)
 * - Session management via MCP-Session-Id header
 * - Origin validation for security
 * - CORS headers for browser clients
 *
 * This is OPTIONAL — most local MCP servers use stdio.
 * AI Factory includes this when user needs remote/cloud deployment.
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import { createServer as createHttpServer } from "node:http";

// ---------------------------------------------------------------------------
// Allowed origins (security: prevents DNS rebinding attacks)
// ---------------------------------------------------------------------------
const ALLOWED_ORIGINS = new Set([
  "http://localhost",
  "http://127.0.0.1",
  // {{ALLOWED_ORIGINS}} — AI factory adds production domains
]);

function isOriginAllowed(origin: string | undefined): boolean {
  if (!origin) return true; // Allow requests without Origin (e.g., curl)
  return ALLOWED_ORIGINS.has(origin) ||
    origin.startsWith("http://localhost:") ||
    origin.startsWith("http://127.0.0.1:");
}

// ---------------------------------------------------------------------------
// Start HTTP transport
// ---------------------------------------------------------------------------

export async function startHttpTransport(
  server: McpServer,
  port: number,
  cleanup: () => Promise<void>
): Promise<void> {
  // Track active sessions
  const sessions = new Map<string, StreamableHTTPServerTransport>();

  const httpServer = createHttpServer(async (req, res) => {
    // CORS headers
    res.setHeader("Access-Control-Allow-Origin", "*");
    res.setHeader("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS");
    res.setHeader(
      "Access-Control-Allow-Headers",
      "Content-Type, MCP-Session-Id, MCP-Protocol-Version"
    );
    res.setHeader(
      "Access-Control-Expose-Headers",
      "MCP-Session-Id"
    );

    if (req.method === "OPTIONS") {
      res.writeHead(204);
      res.end();
      return;
    }

    // Origin validation
    if (!isOriginAllowed(req.headers.origin)) {
      res.writeHead(403, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ error: "Forbidden: invalid origin" }));
      return;
    }

    const url = new URL(req.url ?? "/", `http://localhost:${port}`);

    // Health check endpoint
    if (url.pathname === "/health") {
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ status: "ok", sessions: sessions.size }));
      return;
    }

    // MCP endpoint
    if (url.pathname === "/mcp") {
      const sessionId = req.headers["mcp-session-id"] as string | undefined;

      if (req.method === "POST" && !sessionId) {
        // New session — create transport
        const transport = new StreamableHTTPServerTransport("/mcp", res);
        sessions.set(transport.sessionId, transport);
        await server.connect(transport);
        await transport.handleRequest(req, res);
        return;
      }

      if (sessionId && sessions.has(sessionId)) {
        const transport = sessions.get(sessionId)!;
        await transport.handleRequest(req, res);
        return;
      }

      if (req.method === "DELETE" && sessionId) {
        sessions.delete(sessionId);
        res.writeHead(200);
        res.end();
        return;
      }

      res.writeHead(400, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ error: "Invalid or missing session" }));
      return;
    }

    res.writeHead(404);
    res.end("Not found");
  });

  httpServer.listen(port, "127.0.0.1", () => {
    console.error(`[HTTP] MCP server listening on http://127.0.0.1:${port}/mcp`);
  });

  // Graceful shutdown
  process.on("SIGINT", async () => {
    console.error("[HTTP] Shutting down...");
    await cleanup();
    httpServer.close();
    process.exit(0);
  });
}
