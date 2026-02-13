/**
 * Server Factory
 *
 * Creates and configures the MCP server with all capabilities.
 * This is the central wiring point — tools, resources, and prompts
 * are registered here.
 *
 * Your AI factory will dynamically import and register only the
 * tools/resources/prompts that the user needs.
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { registerTools } from "../tools/index.js";
import { registerResources } from "../resources/index.js";
import { registerPrompts } from "../prompts/index.js";

// ---------------------------------------------------------------------------
// Server metadata — replaced by AI factory during generation
// ---------------------------------------------------------------------------

const SERVER_NAME = "{{SERVER_NAME}}";
const SERVER_VERSION = "{{SERVER_VERSION}}";

// ---------------------------------------------------------------------------
// Server capabilities — AI factory enables only what's needed
// ---------------------------------------------------------------------------

interface ServerCapabilities {
  tools?: boolean;
  resources?: boolean;
  prompts?: boolean;
  logging?: boolean;
}

const CAPABILITIES: ServerCapabilities = {
  tools: true,           // {{ENABLE_TOOLS}}
  resources: false,      // {{ENABLE_RESOURCES}}
  prompts: false,        // {{ENABLE_PROMPTS}}
  logging: true,         // Always useful
};

// ---------------------------------------------------------------------------
// Factory function
// ---------------------------------------------------------------------------

export function createServer(): { server: McpServer; cleanup: () => Promise<void> } {
  const server = new McpServer(
    {
      name: SERVER_NAME,
      version: SERVER_VERSION,
    },
    {
      capabilities: {
        ...(CAPABILITIES.tools && { tools: { listChanged: true } }),
        ...(CAPABILITIES.resources && {
          resources: { subscribe: true, listChanged: true },
        }),
        ...(CAPABILITIES.prompts && { prompts: { listChanged: true } }),
        ...(CAPABILITIES.logging && { logging: {} }),
      },
    }
  );

  // Register capabilities based on what's enabled
  if (CAPABILITIES.tools) {
    registerTools(server);
  }

  if (CAPABILITIES.resources) {
    registerResources(server);
  }

  if (CAPABILITIES.prompts) {
    registerPrompts(server);
  }

  // Cleanup function for graceful shutdown
  const cleanup = async (): Promise<void> => {
    // {{CLEANUP_LOGIC}} — AI factory adds cleanup for DB connections, API clients, etc.
    console.error(`[${SERVER_NAME}] Shutting down...`);
  };

  console.error(`[${SERVER_NAME}] v${SERVER_VERSION} initialized`);

  return { server, cleanup };
}
