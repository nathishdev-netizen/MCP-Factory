from __future__ import annotations

import asyncio
import logging
import re
from pathlib import Path
from typing import Awaitable, Callable

from app.models.architecture import MCPArchitecture, PromptDefinition
from app.services.llm_client import llm_client
from app.codegen.prompts import build_prompt_prompt

log = logging.getLogger("mcp.codegen.prompts")

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
    """Fix common LLM mistakes in generated prompt code."""
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


def _validate_code(code: str, language: str, prompt_name: str) -> None:
    """Basic validation that the generated code has expected structure."""
    if language == "typescript":
        if "export function" not in code and "export const" not in code:
            raise ValueError(f"Generated TS code for prompt '{prompt_name}' missing export function")
    else:
        if "def register_" not in code and "@mcp.prompt" not in code:
            raise ValueError(f"Generated Python code for prompt '{prompt_name}' missing register function or decorator")


def _get_prompt_path(dest_dir: Path, language: str, file_name: str) -> Path:
    """Get the file path for a prompt implementation."""
    if language == "typescript":
        return dest_dir / "src" / "prompts" / file_name
    else:
        return dest_dir / "src" / "mcp_server_template" / "prompts" / file_name


class PromptCodeGenerator:
    async def generate_all_prompts(
        self,
        dest_dir: Path,
        arch: MCPArchitecture,
        progress_callback: ProgressCallback | None = None,
    ) -> None:
        """Generate implementation code for each prompt and write the files."""
        total = len(arch.prompts)
        if total == 0:
            log.info("No prompts to generate")
            return

        delay = 1.0 if total > 10 else 0.0

        for i, prompt in enumerate(arch.prompts):
            if progress_callback:
                await progress_callback(f"Generating prompt: {prompt.name}", i + 1, total)

            log.info("Generating prompt %d/%d: %s", i + 1, total, prompt.name)
            code = await self._generate_with_retry(arch, prompt)

            prompt_path = _get_prompt_path(dest_dir, arch.language, prompt.file_name)
            prompt_path.parent.mkdir(parents=True, exist_ok=True)
            prompt_path.write_text(code, encoding="utf-8")
            log.info("Wrote prompt file: %s (%d chars)", prompt_path.name, len(code))

            if delay > 0 and i < total - 1:
                await asyncio.sleep(delay)

    async def _generate_with_retry(
        self,
        arch: MCPArchitecture,
        prompt: PromptDefinition,
        max_retries: int = 2,
    ) -> str:
        """Generate code for a single prompt with retry logic."""
        last_error: Exception | None = None

        for attempt in range(max_retries):
            try:
                messages = build_prompt_prompt(arch, prompt)
                response = await llm_client.chat_text(messages)
                code = _extract_code(response)
                code = _postprocess_code(code, arch.language)
                _validate_code(code, arch.language, prompt.name)
                return code
            except Exception as e:
                last_error = e
                log.warning(
                    "Prompt generation failed for '%s' (attempt %d/%d): %s",
                    prompt.name, attempt + 1, max_retries, e,
                )
                if attempt < max_retries - 1:
                    await asyncio.sleep(3)

        raise RuntimeError(
            f"Failed to generate prompt '{prompt.name}' after {max_retries} attempts: {last_error}"
        )
