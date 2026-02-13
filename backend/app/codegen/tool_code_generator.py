from __future__ import annotations

import asyncio
import logging
import re
from pathlib import Path
from typing import Awaitable, Callable

from app.models.architecture import MCPArchitecture, ToolDefinition
from app.services.llm_client import llm_client
from app.codegen.prompts import build_tool_prompt

log = logging.getLogger("mcp.codegen.tools")

ProgressCallback = Callable[[str, int, int], Awaitable[None]]


def _extract_code(response: str) -> str:
    """Extract code from LLM response, stripping markdown fences if present."""
    # Try to extract from ```typescript/python ... ``` fences
    fence_match = re.search(
        r"```(?:typescript|python|ts|py|javascript|js)?\s*\n(.*?)```",
        response,
        re.DOTALL,
    )
    if fence_match:
        return fence_match.group(1).strip()

    # If no fences, find the first code-like line and take from there
    lines = response.strip().split("\n")
    code_starts = ("import ", "from ", "//", '"""', "/**", "#!", "export ", "def ", "class ", "const ", "let ", "var ")
    for i, line in enumerate(lines):
        if line.strip().startswith(code_starts):
            # Take everything from this line, but strip any trailing ``` that might be at the end
            code = "\n".join(lines[i:]).strip()
            # Remove trailing ``` if present
            code = re.sub(r"\n```\s*$", "", code)
            return code

    # Fallback: return as-is but strip any trailing fences
    result = response.strip()
    result = re.sub(r"\n```\s*$", "", result)
    return result


def _postprocess_code(code: str, language: str) -> str:
    """Fix common LLM mistakes in generated code."""
    if language == "python":
        # Fix wrong FastMCP import
        code = code.replace("from fastmcp import FastMCP", "from mcp.server.fastmcp import FastMCP")
        # Remove dotenv imports and calls (env vars should use os.environ directly)
        code = re.sub(r"^from dotenv import load_dotenv\n?", "", code, flags=re.MULTILINE)
        code = re.sub(r"^import dotenv\n?", "", code, flags=re.MULTILINE)
        code = re.sub(r"^load_dotenv\(\)\n?", "", code, flags=re.MULTILINE)
    elif language == "typescript":
        # Fix wrong SDK import paths
        code = code.replace(
            'from "@modelcontextprotocol/sdk/server/mcp"',
            'from "@modelcontextprotocol/sdk/server/mcp.js"',
        )

    # Strip any remaining trailing markdown fences
    code = re.sub(r"\n```\s*$", "", code)

    return code


def _validate_code(code: str, language: str, tool_name: str) -> None:
    """Basic validation that the generated code has expected structure."""
    if language == "typescript":
        if "export function" not in code and "export const" not in code:
            raise ValueError(f"Generated TS code for '{tool_name}' missing export function")
    else:
        if "def register_" not in code and "@mcp.tool()" not in code:
            raise ValueError(f"Generated Python code for '{tool_name}' missing register function or decorator")


def _get_tool_path(dest_dir: Path, language: str, file_name: str) -> Path:
    """Get the file path for a tool implementation."""
    if language == "typescript":
        return dest_dir / "src" / "tools" / file_name
    else:
        return dest_dir / "src" / "mcp_server_template" / "tools" / file_name


class ToolCodeGenerator:
    async def generate_all_tools(
        self,
        dest_dir: Path,
        arch: MCPArchitecture,
        progress_callback: ProgressCallback | None = None,
    ) -> None:
        """Generate implementation code for each tool and write the files."""
        total = len(arch.tools)
        if total == 0:
            log.info("No tools to generate")
            return

        delay = 1.0 if total > 10 else 0.0

        for i, tool in enumerate(arch.tools):
            if progress_callback:
                await progress_callback(f"Generating tool: {tool.name}", i + 1, total)

            log.info("Generating tool %d/%d: %s", i + 1, total, tool.name)
            code = await self._generate_with_retry(arch, tool)

            tool_path = _get_tool_path(dest_dir, arch.language, tool.file_name)
            tool_path.parent.mkdir(parents=True, exist_ok=True)
            tool_path.write_text(code, encoding="utf-8")
            log.info("Wrote tool file: %s (%d chars)", tool_path.name, len(code))

            if delay > 0 and i < total - 1:
                await asyncio.sleep(delay)

    async def _generate_with_retry(
        self,
        arch: MCPArchitecture,
        tool: ToolDefinition,
        max_retries: int = 2,
    ) -> str:
        """Generate code for a single tool with retry logic."""
        last_error: Exception | None = None

        for attempt in range(max_retries):
            try:
                messages = build_tool_prompt(arch, tool)
                response = await llm_client.chat_text(messages)
                code = _extract_code(response)
                code = _postprocess_code(code, arch.language)
                _validate_code(code, arch.language, tool.name)
                return code
            except Exception as e:
                last_error = e
                log.warning(
                    "Tool generation failed for '%s' (attempt %d/%d): %s",
                    tool.name, attempt + 1, max_retries, e,
                )
                if attempt < max_retries - 1:
                    await asyncio.sleep(3)

        raise RuntimeError(
            f"Failed to generate tool '{tool.name}' after {max_retries} attempts: {last_error}"
        )
