/**
 * Error Utilities
 *
 * Standardized error handling for MCP tool execution.
 * Converts any error into a proper MCP tool error response.
 */

import type { CallToolResult } from "@modelcontextprotocol/sdk/types.js";

/**
 * Wraps a tool handler with standardized error handling.
 * Catches any thrown error and returns it as an MCP tool error
 * (isError: true) so the LLM can see what went wrong and retry.
 */
export function withErrorHandling(
  toolName: string,
  handler: (...args: unknown[]) => Promise<CallToolResult>
): (...args: unknown[]) => Promise<CallToolResult> {
  return async (...args) => {
    try {
      return await handler(...args);
    } catch (error) {
      const message =
        error instanceof Error ? error.message : String(error);

      // Log to stderr for debugging
      console.error(`[${toolName}] Error: ${message}`);

      // Return error to the LLM (it can self-correct based on this)
      return {
        content: [
          {
            type: "text" as const,
            text: `Tool "${toolName}" failed: ${message}`,
          },
        ],
        isError: true,
      };
    }
  };
}

/**
 * Validates that required environment variables are set.
 * Call this at server startup for tools that need API keys.
 */
export function requireEnvVars(vars: string[]): void {
  const missing = vars.filter((v) => !process.env[v]);
  if (missing.length > 0) {
    throw new Error(
      `Missing required environment variables: ${missing.join(", ")}`
    );
  }
}
