from __future__ import annotations

import asyncio
import logging
import re
from pathlib import Path
from typing import Awaitable, Callable

from app.models.architecture import MCPArchitecture, ResourceDefinition
from app.services.llm_client import llm_client
from app.codegen.prompts import build_resource_prompt

log = logging.getLogger("mcp.codegen.resources")

ProgressCallback = Callable[[str, int, int], Awaitable[None]]


def _extract_code(response: str) -> str:
    """Extract code from LLM response, stripping markdown fences if present."""
    fence_match = re.search(
        r"```(?:typescript|python|ts|py|javascript|js)?\s*\n(.*?)```",
        response,
        re.DOTALL,
    )
    if fence_match:
        return fence_match.group(1).strip()

    lines = response.strip().split("\n")
    code_starts = ("import ", "from ", "//", '"""', "/**", "#!", "export ", "def ", "class ", "const ", "let ", "var ")
    for i, line in enumerate(lines):
        if line.strip().startswith(code_starts):
            code = "\n".join(lines[i:]).strip()
            code = re.sub(r"\n```\s*$", "", code)
            return code

    result = response.strip()
    result = re.sub(r"\n```\s*$", "", result)
    return result


def _postprocess_code(code: str, language: str) -> str:
    """Fix common LLM mistakes in generated resource code."""
    if language == "python":
        code = code.replace("from fastmcp import FastMCP", "from mcp.server.fastmcp import FastMCP")
        code = re.sub(r"^from dotenv import load_dotenv\n?", "", code, flags=re.MULTILINE)
        code = re.sub(r"^import dotenv\n?", "", code, flags=re.MULTILINE)
        code = re.sub(r"^load_dotenv\(\)\n?", "", code, flags=re.MULTILINE)
    elif language == "typescript":
        code = code.replace(
            'from "@modelcontextprotocol/sdk/server/mcp"',
            'from "@modelcontextprotocol/sdk/server/mcp.js"',
        )
    code = re.sub(r"\n```\s*$", "", code)
    return code


def _validate_code(code: str, language: str, resource_name: str) -> None:
    """Basic validation that the generated code has expected structure."""
    if language == "typescript":
        if "export function" not in code and "export const" not in code:
            raise ValueError(f"Generated TS code for resource '{resource_name}' missing export function")
    else:
        if "def register_" not in code and "@mcp.resource" not in code:
            raise ValueError(f"Generated Python code for resource '{resource_name}' missing register function or decorator")


def _get_resource_path(dest_dir: Path, language: str, file_name: str) -> Path:
    """Get the file path for a resource implementation."""
    if language == "typescript":
        return dest_dir / "src" / "resources" / file_name
    else:
        return dest_dir / "src" / "mcp_server_template" / "resources" / file_name


class ResourceCodeGenerator:
    async def generate_all_resources(
        self,
        dest_dir: Path,
        arch: MCPArchitecture,
        progress_callback: ProgressCallback | None = None,
    ) -> None:
        """Generate implementation code for each resource and write the files."""
        total = len(arch.resources)
        if total == 0:
            log.info("No resources to generate")
            return

        delay = 1.0 if total > 10 else 0.0

        for i, resource in enumerate(arch.resources):
            if progress_callback:
                await progress_callback(f"Generating resource: {resource.name}", i + 1, total)

            log.info("Generating resource %d/%d: %s", i + 1, total, resource.name)
            code = await self._generate_with_retry(arch, resource)

            resource_path = _get_resource_path(dest_dir, arch.language, resource.file_name)
            resource_path.parent.mkdir(parents=True, exist_ok=True)
            resource_path.write_text(code, encoding="utf-8")
            log.info("Wrote resource file: %s (%d chars)", resource_path.name, len(code))

            if delay > 0 and i < total - 1:
                await asyncio.sleep(delay)

    async def _generate_with_retry(
        self,
        arch: MCPArchitecture,
        resource: ResourceDefinition,
        max_retries: int = 2,
    ) -> str:
        """Generate code for a single resource with retry logic."""
        last_error: Exception | None = None

        for attempt in range(max_retries):
            try:
                messages = build_resource_prompt(arch, resource)
                response = await llm_client.chat_text(messages)
                code = _extract_code(response)
                code = _postprocess_code(code, arch.language)
                _validate_code(code, arch.language, resource.name)
                return code
            except Exception as e:
                last_error = e
                log.warning(
                    "Resource generation failed for '%s' (attempt %d/%d): %s",
                    resource.name, attempt + 1, max_retries, e,
                )
                if attempt < max_retries - 1:
                    await asyncio.sleep(3)

        raise RuntimeError(
            f"Failed to generate resource '{resource.name}' after {max_retries} attempts: {last_error}"
        )
