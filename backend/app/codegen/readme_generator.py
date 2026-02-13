from __future__ import annotations

import json
import logging
from pathlib import Path

from app.models.architecture import MCPArchitecture
from app.codegen.validator import ValidationResult

log = logging.getLogger("mcp.codegen.readme")


def generate_readme(arch: MCPArchitecture, validation: ValidationResult) -> str:
    """Generate a complete README.md deterministically from architecture data."""
    sections = [
        _title_section(arch),
        _features_section(arch),
        _quickstart_section(arch),
        _client_config_section(arch),
        _tools_section(arch),
        _resources_section(arch),
        _prompts_section(arch),
        _env_vars_section(arch),
        _development_section(arch),
        _notes_section(validation),
    ]
    return "\n\n".join(s for s in sections if s) + "\n"


# ── Individual sections ──────────────────────────────────────────────────


def _title_section(arch: MCPArchitecture) -> str:
    return f"# mcp-server-{arch.server_name}\n\n{arch.server_description}"


def _features_section(arch: MCPArchitecture) -> str:
    lines = ["## Features", ""]
    if arch.tools:
        lines.append(f"- **{len(arch.tools)} Tools** — actions the LLM can perform")
    if arch.enable_resources and arch.resources:
        lines.append(f"- **{len(arch.resources)} Resources** — read-only data the LLM can access")
    if arch.enable_prompts and arch.prompts:
        lines.append(f"- **{len(arch.prompts)} Prompts** — reusable workflow templates")
    lines.append("- Supports **stdio** (local) and **HTTP** (remote) transports")
    lines.append("- Ready-to-use MCP client configuration included")
    return "\n".join(lines)


def _quickstart_section(arch: MCPArchitecture) -> str:
    pkg = f"mcp-server-{arch.server_name}"

    if arch.language == "python":
        return f"""## Quick Start

### Prerequisites
- Python 3.10 or higher
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

### Install & Run
```bash
# Install dependencies
uv sync

# Run the server (stdio mode — used by MCP clients)
uv run {pkg}

# Run with verbose logging
uv run {pkg} -vv

# Run with HTTP transport (for remote/cloud deployments)
uv run {pkg} --transport http --port 3000
```"""
    else:
        return f"""## Quick Start

### Prerequisites
- Node.js 18 or higher
- npm or yarn

### Install & Run
```bash
# Install dependencies
npm install

# Build
npm run build

# Run the server (stdio mode — used by MCP clients)
node dist/index.js

# Run with HTTP transport
node dist/index.js --transport http --port 3000
```"""


def _client_config_section(arch: MCPArchitecture) -> str:
    pkg = f"mcp-server-{arch.server_name}"
    env_block = {}
    for var in arch.env_vars:
        env_block[var.name] = var.example or f"your-{var.name.lower().replace('_', '-')}-here"

    if arch.language == "python":
        server_config = {
            "command": "uv",
            "args": ["--directory", f"/path/to/{pkg}", "run", pkg],
        }
    else:
        server_config = {
            "command": "node",
            "args": [f"/path/to/{pkg}/dist/index.js"],
        }

    if env_block:
        server_config["env"] = env_block

    config = {arch.server_name: server_config}
    config_json = json.dumps(config, indent=2)

    lines = [
        "## MCP Client Configuration",
        "",
        "Add the following to your MCP client configuration.",
        "",
        "### Claude Desktop",
        "",
        f"Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or "
        f"`%APPDATA%\\Claude\\claude_desktop_config.json` (Windows):",
        "",
        "```json",
        "{",
        '  "mcpServers": ' + config_json,
        "}",
        "```",
        "",
        "### Cursor",
        "",
        "Edit `.cursor/mcp.json` in your project root:",
        "",
        "```json",
        "{",
        '  "mcpServers": ' + config_json,
        "}",
        "```",
        "",
        "### Windsurf / Other MCP Clients",
        "",
        "Use the same `mcpServers` JSON block in your client's MCP configuration.",
        "",
        f"> **Note:** Replace `/path/to/{pkg}` with the actual path where you extracted this project.",
    ]
    return "\n".join(lines)


def _tools_section(arch: MCPArchitecture) -> str:
    if not arch.tools:
        return ""

    lines = [
        "## Tools",
        "",
        "| Tool | Description | Parameters |",
        "| --- | --- | --- |",
    ]
    for t in arch.tools:
        params = ", ".join(
            f"`{p.name}` ({p.type}{'*' if p.required else ''})"
            for p in t.parameters
        )
        lines.append(f"| `{t.name}` | {t.description} | {params or 'None'} |")

    lines.append("")
    lines.append("*Parameters marked with `*` are required.*")
    return "\n".join(lines)


def _resources_section(arch: MCPArchitecture) -> str:
    if not arch.enable_resources or not arch.resources:
        return ""

    lines = [
        "## Resources",
        "",
        "| URI | Name | Description | MIME Type |",
        "| --- | --- | --- | --- |",
    ]
    for r in arch.resources:
        lines.append(f"| `{r.uri_template}` | {r.name} | {r.description} | {r.mime_type} |")
    return "\n".join(lines)


def _prompts_section(arch: MCPArchitecture) -> str:
    if not arch.enable_prompts or not arch.prompts:
        return ""

    lines = [
        "## Prompts",
        "",
        "| Prompt | Description | Arguments |",
        "| --- | --- | --- |",
    ]
    for p in arch.prompts:
        args = ", ".join(
            f"`{a.name}` ({a.type}{'*' if a.required else ''})"
            for a in p.arguments
        )
        lines.append(f"| `{p.name}` | {p.description} | {args or 'None'} |")
    return "\n".join(lines)


def _env_vars_section(arch: MCPArchitecture) -> str:
    if not arch.env_vars:
        return ""

    lines = [
        "## Environment Variables",
        "",
        "Copy `.env.example` to `.env` and fill in your values.",
        "",
        "| Variable | Description | Required | Example |",
        "| --- | --- | --- | --- |",
    ]
    for v in arch.env_vars:
        req = "Yes" if v.required else "No"
        lines.append(f"| `{v.name}` | {v.description} | {req} | `{v.example}` |")
    return "\n".join(lines)


def _development_section(arch: MCPArchitecture) -> str:
    if arch.language == "python":
        return """## Development

```bash
# Install dev dependencies
uv sync --group dev

# Run tests
uv run pytest

# Type checking
uv run pyright

# Linting
uv run ruff check .
```"""
    else:
        return """## Development

```bash
# Install dependencies
npm install

# Build
npm run build

# Run tests
npm test

# Type checking
npx tsc --noEmit
```"""


def _notes_section(validation: ValidationResult) -> str:
    if not validation.warnings:
        return ""

    lines = ["## Notes", "", "The following issues were detected during generation:", ""]
    for warning in validation.warnings:
        lines.append(f"- {warning}")
    return "\n".join(lines)
