/**
 * Prompts Registry
 *
 * Imports and registers all prompts with the MCP server.
 * Each prompt lives in its own file — same pattern as tools.
 * Prompts are USER-controlled reusable templates that guide LLM workflows.
 *
 * AI Factory behavior:
 * - Generates individual prompt files (e.g., summarize.ts, daily-report.ts)
 * - Adds import + registration call here for each prompt
 * - Each prompt file exports a `register<Name>Prompt(server)` function
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";

// {{PROMPT_IMPORTS}} — AI factory adds imports here dynamically
// Example:
// import { registerSummarizePrompt } from "./summarize.js";
// import { registerDailyReportPrompt } from "./daily-report.js";

export function registerPrompts(server: McpServer): void {
  // {{PROMPT_REGISTRATIONS}} — AI factory adds registrations here dynamically
  // Example:
  // registerSummarizePrompt(server);
  // registerDailyReportPrompt(server);

  console.error(`[Prompts] Registered all prompts`);
}
