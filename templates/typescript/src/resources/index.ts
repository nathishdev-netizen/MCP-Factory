/**
 * Resources Registry
 *
 * Imports and registers all resources with the MCP server.
 * Each resource lives in its own file — same pattern as tools.
 * Resources are READ-ONLY data endpoints accessed via URI templates.
 *
 * AI Factory behavior:
 * - Generates individual resource files (e.g., server-status.ts, todo-list.ts)
 * - Adds import + registration call here for each resource
 * - Each resource file exports a `register<Name>Resource(server)` function
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";

// {{RESOURCE_IMPORTS}} — AI factory adds imports here dynamically
// Example:
// import { registerServerStatusResource } from "./server-status.js";
// import { registerTodoListResource } from "./todo-list.js";

export function registerResources(server: McpServer): void {
  // {{RESOURCE_REGISTRATIONS}} — AI factory adds registrations here dynamically
  // Example:
  // registerServerStatusResource(server);
  // registerTodoListResource(server);

  console.error(`[Resources] Registered all resources`);
}
