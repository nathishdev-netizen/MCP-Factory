/**
 * Validation Utilities
 *
 * Input sanitization and validation helpers.
 * Security is critical — these protect against injection attacks,
 * path traversal, and other common vulnerabilities.
 */

import path from "node:path";
import { realpathSync } from "node:fs";

/**
 * Validates and normalizes a file path against allowed directories.
 * Prevents path traversal attacks (../../etc/passwd).
 *
 * Used by tools that access the filesystem.
 */
export function validatePath(
  requestedPath: string,
  allowedDirectories: string[]
): string {
  // Resolve to absolute path (handles .., symlinks, etc.)
  const resolved = path.resolve(requestedPath);

  // Resolve symlinks to get real path
  let realPath: string;
  try {
    realPath = realpathSync(resolved);
  } catch {
    // If file doesn't exist yet, use the resolved path
    realPath = resolved;
  }

  // Check if the real path falls within any allowed directory
  const isAllowed = allowedDirectories.some((dir) => {
    const resolvedDir = path.resolve(dir);
    return realPath.startsWith(resolvedDir + path.sep) || realPath === resolvedDir;
  });

  if (!isAllowed) {
    throw new Error(
      `Access denied: "${requestedPath}" is outside allowed directories`
    );
  }

  return realPath;
}

/**
 * Sanitizes a string to prevent command injection.
 * Strips shell metacharacters.
 */
export function sanitizeForShell(input: string): string {
  return input.replace(/[;&|`$(){}[\]<>!#*?~\n\r]/g, "");
}

/**
 * Validates a URL string.
 */
export function validateUrl(input: string): URL {
  try {
    return new URL(input);
  } catch {
    throw new Error(`Invalid URL: "${input}"`);
  }
}
