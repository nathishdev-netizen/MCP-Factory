from __future__ import annotations

import logging
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Awaitable, Callable

from app.models.architecture import MCPArchitecture
from app.codegen.template_copier import copy_template
from app.codegen.placeholder_replacer import replace_all
from app.codegen.code_block_generator import generate_blocks
from app.codegen.tool_code_generator import ToolCodeGenerator
from app.codegen.resource_code_generator import ResourceCodeGenerator
from app.codegen.prompt_code_generator import PromptCodeGenerator
from app.codegen.package_renamer import rename_if_python
from app.codegen.validator import validate_project, regenerate_env_example
from app.codegen.client_config_generator import generate_client_configs
from app.codegen.test_generator import generate_test_file
from app.codegen.readme_generator import generate_readme
from app.codegen.zip_packager import create_zip

log = logging.getLogger("mcp.codegen.generator")

ProgressCallback = Callable[[str, int, int], Awaitable[None]]


@dataclass
class GenerationResult:
    """Result of code generation — ZIP path + project directory for deployment."""
    zip_path: Path
    project_dir: Path


class CodeGenerator:
    def __init__(self) -> None:
        self._tool_generator = ToolCodeGenerator()
        self._resource_generator = ResourceCodeGenerator()
        self._prompt_generator = PromptCodeGenerator()

    async def generate(
        self,
        architecture: MCPArchitecture,
        progress_callback: ProgressCallback | None = None,
    ) -> GenerationResult:
        """Generate a complete MCP server project from an architecture spec.

        Returns a GenerationResult with zip_path and project_dir.
        The project_dir is preserved for auto-deployment (caller must clean up).
        """
        tool_count = len(architecture.tools)
        resource_count = len(architecture.resources) if architecture.enable_resources else 0
        prompt_count = len(architecture.prompts) if architecture.enable_prompts else 0

        # Total steps:
        #   copy(1) + placeholders(1) + blocks(1)
        #   + tools(N) + resources(M) + prompts(P)
        #   + rename(1)
        #   + validate(1) + env(1) + configs(1) + tests(1) + readme(1)
        #   + zip(1)
        total_steps = tool_count + resource_count + prompt_count + 10
        step = 0

        async def progress(msg: str) -> None:
            nonlocal step
            step += 1
            log.info("Step %d/%d: %s", step, total_steps, msg)
            if progress_callback:
                await progress_callback(msg, step, total_steps)

        temp_dir = Path(tempfile.mkdtemp(prefix="mcpgen_"))
        log.info("Working directory: %s", temp_dir)

        try:
            # Step 1: Copy template
            await progress("Copying template")
            copy_template(architecture.language, temp_dir)

            # Step 2: Replace simple placeholders
            await progress("Replacing placeholders")
            replace_all(temp_dir, architecture)

            # Step 3: Generate and inject code blocks (imports, registrations, deps)
            await progress("Generating imports and registrations")
            generate_blocks(temp_dir, architecture)

            # Step 4-N: LLM-powered tool code generation
            async def tool_progress(msg: str, current: int, total: int) -> None:
                nonlocal step
                step = 3 + current
                log.info("Step %d/%d: %s", step, total_steps, msg)
                if progress_callback:
                    await progress_callback(msg, step, total_steps)

            await self._tool_generator.generate_all_tools(
                temp_dir, architecture, progress_callback=tool_progress
            )

            # LLM-powered resource code generation
            if resource_count > 0:
                async def resource_progress(msg: str, current: int, total: int) -> None:
                    nonlocal step
                    step = 3 + tool_count + current
                    log.info("Step %d/%d: %s", step, total_steps, msg)
                    if progress_callback:
                        await progress_callback(msg, step, total_steps)

                await self._resource_generator.generate_all_resources(
                    temp_dir, architecture, progress_callback=resource_progress
                )

            # LLM-powered prompt code generation
            if prompt_count > 0:
                async def prompt_progress(msg: str, current: int, total: int) -> None:
                    nonlocal step
                    step = 3 + tool_count + resource_count + current
                    log.info("Step %d/%d: %s", step, total_steps, msg)
                    if progress_callback:
                        await progress_callback(msg, step, total_steps)

                await self._prompt_generator.generate_all_prompts(
                    temp_dir, architecture, progress_callback=prompt_progress
                )

            # Rename Python package if needed
            await progress("Finalizing project structure")
            rename_if_python(temp_dir, architecture)

            # ── NEW: Validation & Packaging (Steps 4+5) ──

            # Validate generated code
            await progress("Validating generated code")
            validation = validate_project(temp_dir, architecture)
            if validation.errors:
                log.warning("Validation errors: %s", validation.errors)

            # Regenerate .env.example with discovered env vars
            await progress("Updating environment configuration")
            regenerate_env_example(temp_dir, architecture, validation.discovered_env_vars)

            # Generate MCP client configs (claude_desktop_config.json etc.)
            await progress("Generating MCP client configurations")
            generate_client_configs(temp_dir, architecture)

            # Generate test stubs
            await progress("Generating test stubs")
            generate_test_file(temp_dir, architecture)

            # Generate README.md
            await progress("Generating documentation")
            readme_content = generate_readme(architecture, validation)
            (temp_dir / "README.md").write_text(readme_content, encoding="utf-8")

            # ── End new steps ──

            # Create ZIP
            await progress("Creating ZIP archive")
            zip_path = create_zip(temp_dir, architecture.server_name)

            log.info("Generation complete: %s", zip_path)
            return GenerationResult(zip_path=zip_path, project_dir=temp_dir)

        except Exception:
            log.error("Code generation failed, cleaning up")
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise
