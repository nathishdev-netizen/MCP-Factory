from __future__ import annotations

import json
import logging
from pathlib import Path

from app.models.architecture import MCPArchitecture

log = logging.getLogger("mcp.codegen.clientconfig")


def generate_client_configs(project_dir: Path, arch: MCPArchitecture) -> None:
    """Generate ready-to-paste MCP client configuration files."""
    env_block = _build_env_block(arch)
    pkg_name = f"mcp-server-{arch.server_name}"

    if arch.language == "python":
        server_config = {
            "command": "uv",
            "args": ["--directory", f"/path/to/{pkg_name}", "run", pkg_name],
        }
    else:
        server_config = {
            "command": "node",
            "args": [f"/path/to/{pkg_name}/dist/index.js"],
        }

    if env_block:
        server_config["env"] = env_block

    config = {
        "mcpServers": {
            arch.server_name: server_config
        }
    }

    config_json = json.dumps(config, indent=2) + "\n"

    # Main config file (overwrite template)
    (project_dir / "mcp-client-config.json").write_text(config_json, encoding="utf-8")

    # Claude Desktop specific (separate file for easy copy-paste)
    (project_dir / "claude_desktop_config.json").write_text(config_json, encoding="utf-8")

    log.info("Generated MCP client configs with %d env vars", len(env_block))


def _build_env_block(arch: MCPArchitecture) -> dict[str, str]:
    """Build the env block from architecture env vars."""
    env = {}
    for var in arch.env_vars:
        if var.example:
            env[var.name] = var.example
        else:
            env[var.name] = f"your-{var.name.lower().replace('_', '-')}-here"
    return env
