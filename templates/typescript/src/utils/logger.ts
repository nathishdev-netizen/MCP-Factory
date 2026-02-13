/**
 * Logger Utility
 *
 * CRITICAL MCP RULE: Never use console.log() in an MCP server!
 * stdout is reserved for JSON-RPC messages.
 * All logging MUST go to stderr.
 *
 * This logger writes to stderr and supports structured logging
 * for observability.
 */

type LogLevel = "debug" | "info" | "warn" | "error";

const LOG_LEVELS: Record<LogLevel, number> = {
  debug: 0,
  info: 1,
  warn: 2,
  error: 3,
};

const currentLevel: LogLevel =
  (process.env.LOG_LEVEL as LogLevel) ?? "info";

function shouldLog(level: LogLevel): boolean {
  return LOG_LEVELS[level] >= LOG_LEVELS[currentLevel];
}

function formatMessage(
  level: LogLevel,
  component: string,
  message: string,
  data?: Record<string, unknown>
): string {
  const timestamp = new Date().toISOString();
  const base = `${timestamp} [${level.toUpperCase()}] [${component}] ${message}`;
  if (data) {
    return `${base} ${JSON.stringify(data)}`;
  }
  return base;
}

export function createLogger(component: string) {
  return {
    debug: (msg: string, data?: Record<string, unknown>) => {
      if (shouldLog("debug"))
        console.error(formatMessage("debug", component, msg, data));
    },
    info: (msg: string, data?: Record<string, unknown>) => {
      if (shouldLog("info"))
        console.error(formatMessage("info", component, msg, data));
    },
    warn: (msg: string, data?: Record<string, unknown>) => {
      if (shouldLog("warn"))
        console.error(formatMessage("warn", component, msg, data));
    },
    error: (msg: string, data?: Record<string, unknown>) => {
      if (shouldLog("error"))
        console.error(formatMessage("error", component, msg, data));
    },
  };
}
