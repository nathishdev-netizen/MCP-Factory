from __future__ import annotations

import json
import logging
from pathlib import Path

from app.models.architecture import (
    MCPArchitecture,
    ToolDefinition,
    ResourceDefinition,
    PromptDefinition,
    Dependency,
    EnvVar,
)

log = logging.getLogger("mcp.codegen.blocks")


# ── Name helpers ──────────────────────────────────────────────────────────


def _to_register_func_ts(tool_name: str) -> str:
    """Convert 'issues.create' → 'registerIssuesCreateTool'."""
    parts = tool_name.replace("-", ".").split(".")
    camel = "".join(p.capitalize() for p in parts)
    return f"register{camel}Tool"


def _to_register_func_py(tool_name: str) -> str:
    """Convert 'issues.create' → 'register_issues_create_tool'."""
    snake = tool_name.replace(".", "_").replace("-", "_")
    return f"register_{snake}_tool"


# ── TypeScript blocks ─────────────────────────────────────────────────────


def _ts_tool_imports(tools: list[ToolDefinition]) -> str:
    lines = []
    for tool in tools:
        module = tool.file_name.replace(".ts", "")
        func = _to_register_func_ts(tool.name)
        lines.append(f'import {{ {func} }} from "./{module}.js";')
    return "\n".join(lines)


def _ts_tool_registrations(tools: list[ToolDefinition]) -> str:
    lines = []
    for tool in tools:
        func = _to_register_func_ts(tool.name)
        lines.append(f"  {func}(server);")
    return "\n".join(lines)


def _slugify(name: str) -> str:
    """Normalize a name by replacing spaces, dots, and hyphens with underscores."""
    return name.replace(" ", "_").replace(".", "_").replace("-", "_").lower()


def _to_register_resource_func_ts(name: str) -> str:
    """Convert 'Todo List' or 'server-status' → 'registerTodoListResource'."""
    parts = _slugify(name).split("_")
    camel = "".join(p.capitalize() for p in parts if p)
    return f"register{camel}Resource"


def _to_register_resource_func_py(name: str) -> str:
    """Convert 'Todo List' or 'server-status' → 'register_todo_list_resource'."""
    snake = _slugify(name)
    return f"register_{snake}_resource"


def _to_register_prompt_func_ts(name: str) -> str:
    """Convert 'daily-report' → 'registerDailyReportPrompt'."""
    parts = _slugify(name).split("_")
    camel = "".join(p.capitalize() for p in parts if p)
    return f"register{camel}Prompt"


def _to_register_prompt_func_py(name: str) -> str:
    """Convert 'daily-report' → 'register_daily_report_prompt'."""
    snake = _slugify(name)
    return f"register_{snake}_prompt"


def _ts_resource_imports(resources: list[ResourceDefinition]) -> str:
    lines = []
    for res in resources:
        module = res.file_name.replace(".ts", "")
        func = _to_register_resource_func_ts(res.name)
        lines.append(f'import {{ {func} }} from "./{module}.js";')
    return "\n".join(lines)


def _ts_resource_registrations(resources: list[ResourceDefinition]) -> str:
    lines = []
    for res in resources:
        func = _to_register_resource_func_ts(res.name)
        lines.append(f"  {func}(server);")
    return "\n".join(lines)


def _ts_prompt_imports(prompts: list[PromptDefinition]) -> str:
    lines = []
    for prompt in prompts:
        module = prompt.file_name.replace(".ts", "")
        func = _to_register_prompt_func_ts(prompt.name)
        lines.append(f'import {{ {func} }} from "./{module}.js";')
    return "\n".join(lines)


def _ts_prompt_registrations(prompts: list[PromptDefinition]) -> str:
    lines = []
    for prompt in prompts:
        func = _to_register_prompt_func_ts(prompt.name)
        lines.append(f"  {func}(server);")
    return "\n".join(lines)


def _ts_extra_dependencies(dest_dir: Path, deps: list[Dependency]) -> None:
    """Add extra dependencies to package.json by parsing and rewriting it."""
    pkg_path = dest_dir / "package.json"
    if not pkg_path.exists():
        return

    pkg = json.loads(pkg_path.read_text(encoding="utf-8"))
    for dep in deps:
        # Use the package name as-is; version from LLM or default "latest"
        parts = dep.package.split(">=")
        name = parts[0].strip()
        version = f"^{parts[1].strip()}" if len(parts) > 1 else "latest"
        pkg.setdefault("dependencies", {})[name] = version

    pkg_path.write_text(json.dumps(pkg, indent=2) + "\n", encoding="utf-8")
    log.info("Added %d extra dependencies to package.json", len(deps))


# ── Python blocks ─────────────────────────────────────────────────────────


def _py_tool_imports(tools: list[ToolDefinition]) -> str:
    lines = []
    for tool in tools:
        module = tool.file_name.replace(".py", "")
        func = _to_register_func_py(tool.name)
        lines.append(f"from .{module} import {func}")
    return "\n".join(lines)


def _py_tool_registrations(tools: list[ToolDefinition]) -> str:
    lines = []
    for tool in tools:
        func = _to_register_func_py(tool.name)
        lines.append(f"    {func}(mcp)")
    return "\n".join(lines)


def _py_resource_imports(resources: list[ResourceDefinition]) -> str:
    lines = []
    for res in resources:
        module = res.file_name.replace(".py", "")
        func = _to_register_resource_func_py(res.name)
        lines.append(f"from .{module} import {func}")
    return "\n".join(lines)


def _py_resource_registrations(resources: list[ResourceDefinition]) -> str:
    lines = []
    for res in resources:
        func = _to_register_resource_func_py(res.name)
        lines.append(f"    {func}(mcp)")
    return "\n".join(lines)


def _py_prompt_imports(prompts: list[PromptDefinition]) -> str:
    lines = []
    for prompt in prompts:
        module = prompt.file_name.replace(".py", "")
        func = _to_register_prompt_func_py(prompt.name)
        lines.append(f"from .{module} import {func}")
    return "\n".join(lines)


def _py_prompt_registrations(prompts: list[PromptDefinition]) -> str:
    lines = []
    for prompt in prompts:
        func = _to_register_prompt_func_py(prompt.name)
        lines.append(f"    {func}(mcp)")
    return "\n".join(lines)


def _py_extra_dependencies(deps: list[Dependency]) -> str:
    # Base packages already in the template — skip duplicates
    base_packages = {"mcp", "pydantic", "click", "fastmcp", "mcp[cli]", "loguru"}
    lines = []
    seen = set()
    for dep in deps:
        pkg_name = dep.package.split(">=")[0].split("==")[0].split(">")[0].split("<")[0].strip().lower()
        if pkg_name in base_packages or pkg_name in seen:
            continue
        seen.add(pkg_name)
        lines.append(f'    "{dep.package}",  # {dep.reason}')
    return "\n".join(lines)


# ── Shared blocks ─────────────────────────────────────────────────────────


def _env_template(env_vars: list[EnvVar]) -> str:
    lines = []
    for var in env_vars:
        req = "required" if var.required else "optional"
        lines.append(f"# {var.description} ({req})")
        lines.append(f"{var.name}={var.example}")
        lines.append("")
    return "\n".join(lines)


def _cleanup_logic_ts(arch: MCPArchitecture) -> str:
    """Generate TypeScript cleanup code based on dependencies."""
    lines = []
    dep_names = {d.package.lower() for d in arch.extra_dependencies}
    if any(x in dep_names for x in ("axios", "node-fetch")):
        lines.append("    // Close HTTP clients if needed")
    if not lines:
        lines.append("    // No special cleanup needed")
    return "\n".join(lines)


def _dockerfile_env_vars(env_vars: list[EnvVar]) -> str:
    lines = []
    for var in env_vars:
        lines.append(f'ENV {var.name}=""')
    return "\n".join(lines)


# ── Injection logic ───────────────────────────────────────────────────────


def _inject_block(file_path: Path, placeholder: str, block: str) -> bool:
    """Replace the line containing the placeholder comment with the generated block.

    Handles both `// {{PLACEHOLDER}}` (TS) and `# {{PLACEHOLDER}}` (Python) styles.
    Also removes the example comment lines that follow the placeholder.
    """
    if not file_path.exists():
        return False

    content = file_path.read_text(encoding="utf-8")
    if placeholder not in content:
        return False

    lines = content.split("\n")
    new_lines = []
    skip_examples = False

    for line in lines:
        if placeholder in line:
            # Replace the placeholder line with the generated block
            if block.strip():
                new_lines.append(block)
            skip_examples = True
            continue

        # Skip example comment lines after the placeholder
        if skip_examples:
            stripped = line.strip()
            if stripped.startswith("//") or stripped.startswith("#"):
                continue
            skip_examples = False

        new_lines.append(line)

    file_path.write_text("\n".join(new_lines), encoding="utf-8")
    return True


# ── Main entry point ──────────────────────────────────────────────────────


def generate_blocks(dest_dir: Path, arch: MCPArchitecture) -> None:
    """Generate and inject all code blocks into template files."""

    if arch.language == "typescript":
        _generate_ts_blocks(dest_dir, arch)
    else:
        _generate_py_blocks(dest_dir, arch)

    # Shared: env template
    for env_file in [dest_dir / ".env.example"]:
        if env_file.exists():
            _inject_block(env_file, "{{ENV_TEMPLATE}}", _env_template(arch.env_vars))

    log.info("Generated and injected all code blocks")


def _generate_ts_blocks(dest_dir: Path, arch: MCPArchitecture) -> None:
    """Generate TypeScript-specific code blocks."""
    tools_index = dest_dir / "src" / "tools" / "index.ts"
    resources_index = dest_dir / "src" / "resources" / "index.ts"
    prompts_index = dest_dir / "src" / "prompts" / "index.ts"
    server_index = dest_dir / "src" / "server" / "index.ts"
    http_transport = dest_dir / "src" / "server" / "http-transport.ts"

    # Tool imports & registrations
    _inject_block(tools_index, "{{TOOL_IMPORTS}}", _ts_tool_imports(arch.tools))
    _inject_block(tools_index, "{{TOOL_REGISTRATIONS}}", _ts_tool_registrations(arch.tools))

    # Resource imports & registrations
    _inject_block(resources_index, "{{RESOURCE_IMPORTS}}", _ts_resource_imports(arch.resources))
    _inject_block(resources_index, "{{RESOURCE_REGISTRATIONS}}", _ts_resource_registrations(arch.resources))

    # Prompt imports & registrations
    _inject_block(prompts_index, "{{PROMPT_IMPORTS}}", _ts_prompt_imports(arch.prompts))
    _inject_block(prompts_index, "{{PROMPT_REGISTRATIONS}}", _ts_prompt_registrations(arch.prompts))

    # Cleanup logic
    _inject_block(server_index, "{{CLEANUP_LOGIC}}", _cleanup_logic_ts(arch))

    # Allowed origins
    _inject_block(http_transport, "{{ALLOWED_ORIGINS}}", "")

    # Extra dependencies (JSON manipulation)
    _ts_extra_dependencies(dest_dir, arch.extra_dependencies)

    # Dockerfile env vars
    dockerfile = dest_dir / "Dockerfile"
    _inject_block(dockerfile, "{{ENV_VARS}}", _dockerfile_env_vars(arch.env_vars))


def _generate_py_blocks(dest_dir: Path, arch: MCPArchitecture) -> None:
    """Generate Python-specific code blocks."""
    pkg_dir = dest_dir / "src" / "mcp_server_template"
    tools_init = pkg_dir / "tools" / "__init__.py"
    resources_init = pkg_dir / "resources" / "__init__.py"
    prompts_init = pkg_dir / "prompts" / "__init__.py"
    pyproject = dest_dir / "pyproject.toml"
    dockerfile = dest_dir / "Dockerfile"
    tests_file = dest_dir / "tests" / "test_tools.py"

    # Tool imports & registrations
    _inject_block(tools_init, "{{TOOL_IMPORTS}}", _py_tool_imports(arch.tools))
    _inject_block(tools_init, "{{TOOL_REGISTRATIONS}}", _py_tool_registrations(arch.tools))

    # Resource imports & registrations
    _inject_block(resources_init, "{{RESOURCE_IMPORTS}}", _py_resource_imports(arch.resources))
    _inject_block(resources_init, "{{RESOURCE_REGISTRATIONS}}", _py_resource_registrations(arch.resources))

    # Prompt imports & registrations
    _inject_block(prompts_init, "{{PROMPT_IMPORTS}}", _py_prompt_imports(arch.prompts))
    _inject_block(prompts_init, "{{PROMPT_REGISTRATIONS}}", _py_prompt_registrations(arch.prompts))

    # Extra dependencies in pyproject.toml
    _inject_block(pyproject, "{{EXTRA_DEPENDENCIES}}", _py_extra_dependencies(arch.extra_dependencies))

    # Dockerfile env vars and system deps
    _inject_block(dockerfile, "{{ENV_VARS}}", _dockerfile_env_vars(arch.env_vars))
    _inject_block(dockerfile, "{{SYSTEM_DEPS}}", "")

    # Test imports
    if tests_file.exists():
        _inject_block(tests_file, "{{TOOL_TEST_IMPORTS}}", "")
