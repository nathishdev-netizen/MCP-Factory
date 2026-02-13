/**
 * Tools Registry
 *
 * This file orchestrates all tool registrations.
 * Each tool lives in its own file for clean separation.
 *
 * AI Factory behavior:
 * - Generates individual tool files (e.g., search-hotels.ts, book-hotel.ts)
 * - Adds import + registration call here for each tool
 * - Each tool file exports a `register<Name>Tool(server)` function
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";

// {{TOOL_IMPORTS}} — AI factory adds imports here dynamically
// Example:
// import { registerSearchHotelsTool } from "./search-hotels.js";
// import { registerBookHotelTool } from "./book-hotel.js";

export function registerTools(server: McpServer): void {
  // {{TOOL_REGISTRATIONS}} — AI factory adds registrations here dynamically
  // Example:
  // registerSearchHotelsTool(server);
  // registerBookHotelTool(server);

  console.error(`[Tools] Registered all tools`);
}
