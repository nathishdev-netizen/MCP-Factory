from __future__ import annotations

from app.models.architecture import (
    MCPArchitecture,
    ToolDefinition,
    ResourceDefinition,
    PromptDefinition,
    EnvVar,
)


def _format_parameters(tool: ToolDefinition) -> str:
    if not tool.parameters:
        return "  (no parameters)"
    lines = []
    for p in tool.parameters:
        req = "REQUIRED" if p.required else f"OPTIONAL (default: {p.default})"
        extras = ""
        if p.enum_values:
            extras += f", enum: {p.enum_values}"
        if p.validation:
            extras += f", validation: {p.validation}"
        lines.append(f"  - {p.name}: {p.type} — {p.description} [{req}]{extras}")
    return "\n".join(lines)


def _format_env_vars(env_vars: list[EnvVar]) -> str:
    if not env_vars:
        return "None"
    return "\n".join(f"  - {v.name}: {v.description}" for v in env_vars)


def _format_dependencies(arch: MCPArchitecture) -> str:
    if not arch.extra_dependencies:
        return "Standard library only"
    return "\n".join(f"  - {d.package}: {d.reason}" for d in arch.extra_dependencies)


def build_tool_prompt(arch: MCPArchitecture, tool: ToolDefinition) -> list[dict]:
    """Build the LLM messages for generating a single tool implementation file."""
    if arch.language == "typescript":
        return _build_ts_prompt(arch, tool)
    return _build_py_prompt(arch, tool)


def _build_ts_prompt(arch: MCPArchitecture, tool: ToolDefinition) -> list[dict]:
    func_name = _to_register_func_ts(tool.name)

    system = f"""You are a code generator that produces TypeScript MCP tool implementation files.
Output ONLY raw TypeScript code. NEVER wrap output in markdown code fences (``` or ```typescript).
No explanation text before or after the code. Just the TypeScript source file content.
The code must be production-ready, with proper error handling and input validation."""

    user = f"""Generate a complete TypeScript MCP tool implementation file.

SERVER: {arch.server_name} — {arch.server_description}

TOOL SPEC:
- Name: {tool.name}
- File: {tool.file_name}
- Description: {tool.description}
- Parameters:
{_format_parameters(tool)}
- Returns: {tool.return_description}
- External API: {tool.external_api or "None"}
- Error scenarios: {", ".join(tool.error_scenarios) if tool.error_scenarios else "Standard errors"}

ENVIRONMENT VARIABLES AVAILABLE:
{_format_env_vars(arch.env_vars)}

AVAILABLE DEPENDENCIES:
{_format_dependencies(arch)}

EXACT FILE PATTERN (follow this precisely):

import {{ McpServer }} from "@modelcontextprotocol/sdk/server/mcp.js";
import {{ z }} from "zod";
import {{ withErrorHandling }} from "../utils/errors.js";

export function {func_name}(server: McpServer) {{
  server.tool(
    "{tool.name}",
    "{tool.description}",
    {{
      // Zod schema for each parameter with .describe()
    }},
    withErrorHandling("{tool.name}", async ({{ /* destructured params */ }}) => {{
      // Implementation here
      return {{ content: [{{ type: "text", text: JSON.stringify(result, null, 2) }}] }};
    }})
  );
}}

CRITICAL RULES:
- Import MUST be: `import {{ McpServer }} from "@modelcontextprotocol/sdk/server/mcp.js";`
- Do NOT add any markdown fences or backticks in output
- Use Zod schemas for ALL parameters with .describe() on each
- Wrap handler with withErrorHandling (from ../utils/errors.js)
- For HTTP API calls: use fetch() (built-in Node 18+)
- Read env vars with process.env.VAR_NAME
- All logging to stderr via console.error()
- Return results as JSON.stringify() in content array
- Handle each error scenario with descriptive messages
- Do NOT use console.log() — only console.error()
- Output ONLY the TypeScript code, no markdown"""

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def _build_py_prompt(arch: MCPArchitecture, tool: ToolDefinition) -> list[dict]:
    register_func = _to_register_func_py(tool.name)
    tool_func = tool.name.replace(".", "_").replace("-", "_")

    # Build typed params string
    typed_params = []
    for p in tool.parameters:
        type_map = {"string": "str", "number": "int", "boolean": "bool", "array": "list", "object": "dict"}
        py_type = type_map.get(p.type, "str")
        if p.required:
            typed_params.append(f"{p.name}: {py_type}")
        else:
            default = f'"{p.default}"' if p.default and py_type == "str" else (p.default or '""')
            typed_params.append(f"{p.name}: {py_type} = {default}")

    params_str = ", ".join(typed_params)

    # Include all sibling tools so the LLM can maintain consistent store usage
    sibling_tools = _format_tools_summary(arch)

    system = f"""You are a code generator that produces Python MCP tool implementation files.
Output ONLY raw Python code. NEVER wrap output in markdown code fences (``` or ```python).
No explanation text before or after the code. Just the Python source file content.
The code must be production-ready with proper error handling and logging."""

    user = f"""Generate a complete Python MCP tool implementation file.

SERVER: {arch.server_name} — {arch.server_description}

ALL TOOLS IN THIS SERVER (you are generating ONE of these — ensure consistent store usage):
{sibling_tools}

TOOL TO GENERATE:
- Name: {tool.name}
- File: {tool.file_name}
- Description: {tool.description}
- Parameters:
{_format_parameters(tool)}
- Returns: {tool.return_description}
- External API: {tool.external_api or "None"}
- Error scenarios: {", ".join(tool.error_scenarios) if tool.error_scenarios else "Standard errors"}

ENVIRONMENT VARIABLES AVAILABLE:
{_format_env_vars(arch.env_vars)}

AVAILABLE DEPENDENCIES:
{_format_dependencies(arch)}

EXACT FILE PATTERN (follow this precisely):

import json
import logging
import os
from mcp.server.fastmcp import FastMCP

from ..utils.store import store

log = logging.getLogger(__name__)

def {register_func}(mcp: FastMCP):
    @mcp.tool()
    async def {tool_func}({params_str}) -> str:
        \\"\\"\\"
        {tool.description}

        Args:
            (document each parameter here)
        \\"\\"\\"
        # Use `store` dict for any shared state (e.g. store[id] = item)
        return json.dumps(result)

SHARED STORE DATA CONVENTION (ALL tools MUST follow this):
- `store` is imported from `..utils.store` — it is a single dict shared across ALL tools and resources
- IDs are ALWAYS strings: generate with `str(uuid.uuid4())` (import uuid). NEVER use int IDs.
- Any parameter that accepts an ID (e.g. task_id, note_id, item_id) MUST be typed as `str`, NEVER `int`
- Store items using their string ID as the key: `store[item_id] = {{"id": item_id, "title": title, ...}}`
- List all items: `list(store.values())` — returns all stored items
- Get one item: `store.get(item_id)` — returns the item or None
- Delete an item: `store.pop(item_id, None)` — removes and returns, or None
- Check existence: `item_id in store`
- NEVER use `store["items"]` or `store["notes"]` or any nested collection key
- NEVER create module-level variables, mcp.state, or separate dicts for storage
- Every item stored MUST include its ID: `store[item_id] = {{"id": item_id, "title": title, ...}}`

CRITICAL RULES:
- Import FastMCP EXACTLY as: `from mcp.server.fastmcp import FastMCP` — NEVER `from fastmcp import FastMCP`
- Use `@mcp.tool()` with NO arguments — NEVER pass readOnlyHint, destructiveHint, or any kwargs to @mcp.tool()
- Do NOT import dotenv or call load_dotenv(). Read env vars directly with os.environ.
- Do NOT add any markdown fences or backticks in output
- The register function MUST be named exactly: {register_func}
- The register function takes `mcp: FastMCP` as its only parameter
- Use Python type hints for ALL parameters
- Use default values for optional params
- Docstring with Args section
- For HTTP API calls: use httpx (async) — `async with httpx.AsyncClient() as client:`
- Read env vars with os.environ.get("VAR_NAME") or os.environ["VAR_NAME"]
- All logging via the logger, NEVER use print()
- Return results as json.dumps()
- Handle errors with try/except and log.error()
- Output ONLY the Python code, no markdown"""

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def _to_register_func_ts(tool_name: str) -> str:
    parts = tool_name.replace("-", ".").split(".")
    camel = "".join(p.capitalize() for p in parts)
    return f"register{camel}Tool"


def _to_register_func_py(tool_name: str) -> str:
    snake = tool_name.replace(".", "_").replace("-", "_")
    return f"register_{snake}_tool"


# ── Resource generation prompts (individual files) ───────────────────────


def _format_tools_summary(arch: MCPArchitecture) -> str:
    return "\n".join(f"  - {t.name}: {t.description}" for t in arch.tools)


def _slugify(name: str) -> str:
    """Normalize a name by replacing spaces, dots, and hyphens with underscores."""
    return name.replace(" ", "_").replace(".", "_").replace("-", "_").lower()


def _to_register_resource_func_ts(name: str) -> str:
    parts = _slugify(name).split("_")
    camel = "".join(p.capitalize() for p in parts if p)
    return f"register{camel}Resource"


def _to_register_resource_func_py(name: str) -> str:
    snake = _slugify(name)
    return f"register_{snake}_resource"


def _to_register_prompt_func_ts(name: str) -> str:
    parts = _slugify(name).split("_")
    camel = "".join(p.capitalize() for p in parts if p)
    return f"register{camel}Prompt"


def _to_register_prompt_func_py(name: str) -> str:
    snake = _slugify(name)
    return f"register_{snake}_prompt"


def build_resource_prompt(arch: MCPArchitecture, resource: ResourceDefinition) -> list[dict]:
    """Build LLM messages for generating a single resource implementation file."""
    if arch.language == "typescript":
        return _build_ts_resource_prompt(arch, resource)
    return _build_py_resource_prompt(arch, resource)


def _build_py_resource_prompt(arch: MCPArchitecture, resource: ResourceDefinition) -> list[dict]:
    register_func = _to_register_resource_func_py(resource.name)
    resource_func = resource.name.lower().replace(" ", "_").replace("-", "_").replace(".", "_")

    # Determine if it's a template URI (has {param})
    import re as _re
    uri_params = _re.findall(r"\{(\w+)\}", resource.uri_template)
    if uri_params:
        params_str = ", ".join(f"{p}: str" for p in uri_params)
        func_sig = f"async def {resource_func}({params_str}) -> str:"
    else:
        func_sig = f"async def {resource_func}() -> str:"

    system = """You are a code generator that produces Python MCP resource implementation files.
Output ONLY raw Python code. NEVER wrap output in markdown code fences (``` or ```python).
No explanation text before or after the code. Just the Python source file content.
The code must be production-ready with proper error handling and logging."""

    user = f"""Generate a complete Python MCP resource implementation file.

SERVER: {arch.server_name} — {arch.server_description}

AVAILABLE TOOLS (resources should complement these):
{_format_tools_summary(arch)}

RESOURCE SPEC:
- Name: {resource.name}
- File: {resource.file_name}
- URI Template: {resource.uri_template}
- Description: {resource.description}
- MIME Type: {resource.mime_type}

ENVIRONMENT VARIABLES AVAILABLE:
{_format_env_vars(arch.env_vars)}

EXACT FILE PATTERN (follow this precisely):

import json
import logging
import os
from mcp.server.fastmcp import FastMCP

from ..utils.store import store

log = logging.getLogger(__name__)

def {register_func}(mcp: FastMCP):
    @mcp.resource("{resource.uri_template}")
    {func_sig}
        \"\"\"
        {resource.description}
        \"\"\"
        # Read from the shared `store` dict (same data written by tools)
        return json.dumps(data)

SHARED STORE DATA CONVENTION (same store used by tools):
- `store` is imported from `..utils.store` — a single dict shared across ALL tools and resources
- All IDs are strings (uuid4). Any parameter accepting an ID MUST be typed as `str`, NEVER `int`
- Tools store items using their string ID as the key: `store[item_id] = {{"id": item_id, ...}}`
- To list all items: `list(store.values())`
- To get one item: `store.get(item_id)`
- NEVER use `store["items"]` or `store["notes"]` or any nested collection key
- NEVER use mcp.call_tool(), mcp.state, or mcp._attr to access data
- NEVER create your own module-level dict/list

CRITICAL RULES:
- Import FastMCP EXACTLY as: `from mcp.server.fastmcp import FastMCP` — NEVER `from fastmcp import FastMCP`
- Do NOT import dotenv or call load_dotenv(). Read env vars directly with os.environ.
- Do NOT add any markdown fences or backticks in output
- The register function MUST be named exactly: {register_func}
- The register function takes `mcp: FastMCP` as its only parameter
- Use @mcp.resource("{resource.uri_template}") decorator
- Resources are READ-ONLY data accessors — never modify data
- Return data as json.dumps() for JSON or plain string for text
- Use logging, NEVER print()
- Handle errors with try/except and log.error()
- Output ONLY the Python code, no markdown"""

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def _build_ts_resource_prompt(arch: MCPArchitecture, resource: ResourceDefinition) -> list[dict]:
    func_name = _to_register_resource_func_ts(resource.name)

    system = """You are a code generator that produces TypeScript MCP resource implementation files.
Output ONLY raw TypeScript code. NEVER wrap output in markdown code fences (``` or ```typescript).
No explanation text before or after the code. Just the TypeScript source file content.
The code must be production-ready with proper error handling."""

    user = f"""Generate a complete TypeScript MCP resource implementation file.

SERVER: {arch.server_name} — {arch.server_description}

RESOURCE SPEC:
- Name: {resource.name}
- File: {resource.file_name}
- URI Template: {resource.uri_template}
- Description: {resource.description}
- MIME Type: {resource.mime_type}

ENVIRONMENT VARIABLES AVAILABLE:
{_format_env_vars(arch.env_vars)}

EXACT FILE PATTERN (follow this precisely):

import {{ McpServer }} from "@modelcontextprotocol/sdk/server/mcp.js";

export function {func_name}(server: McpServer): void {{
  server.resource(
    "{resource.name}",
    "{resource.uri_template}",
    async (uri) => ({{
      contents: [{{
        uri: uri.href,
        mimeType: "{resource.mime_type}",
        text: JSON.stringify(data, null, 2)
      }}]
    }})
  );
}}

CRITICAL RULES:
- Import MUST be: `import {{ McpServer }} from "@modelcontextprotocol/sdk/server/mcp.js";`
- Do NOT add any markdown fences or backticks in output
- The function MUST be named exactly: {func_name}
- Resources are READ-ONLY data accessors — never modify data
- Read env vars with process.env.VAR_NAME
- All logging to stderr via console.error()
- Return contents array with proper mimeType
- Do NOT use console.log() — only console.error()
- Output ONLY the TypeScript code, no markdown"""

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


# ── Prompt generation prompts (individual files) ─────────────────────────


def _format_prompt_arguments(prompt: PromptDefinition) -> str:
    if not prompt.arguments:
        return "  (no arguments)"
    lines = []
    for a in prompt.arguments:
        req = "REQUIRED" if a.required else f"OPTIONAL (default: {a.default})"
        lines.append(f"  - {a.name}: {a.type} — {a.description} [{req}]")
    return "\n".join(lines)


def build_prompt_prompt(arch: MCPArchitecture, prompt: PromptDefinition) -> list[dict]:
    """Build LLM messages for generating a single prompt implementation file."""
    if arch.language == "typescript":
        return _build_ts_prompt_prompt(arch, prompt)
    return _build_py_prompt_prompt(arch, prompt)


def _build_py_prompt_prompt(arch: MCPArchitecture, prompt: PromptDefinition) -> list[dict]:
    register_func = _to_register_prompt_func_py(prompt.name)
    prompt_func = prompt.name.replace(".", "_").replace("-", "_")

    # Build typed params string
    typed_params = []
    for a in prompt.arguments:
        type_map = {"string": "str", "number": "int", "boolean": "bool"}
        py_type = type_map.get(a.type, "str")
        if a.required:
            typed_params.append(f"{a.name}: {py_type}")
        else:
            default = f'"{a.default}"' if a.default and py_type == "str" else (a.default or '""')
            typed_params.append(f"{a.name}: {py_type} = {default}")
    params_str = ", ".join(typed_params)

    system = """You are a code generator that produces Python MCP prompt implementation files.
Output ONLY raw Python code. NEVER wrap output in markdown code fences (``` or ```python).
No explanation text before or after the code. Just the Python source file content.
The code must be production-ready."""

    user = f"""Generate a complete Python MCP prompt implementation file.

SERVER: {arch.server_name} — {arch.server_description}

AVAILABLE TOOLS (prompts should guide the LLM to use these):
{_format_tools_summary(arch)}

PROMPT SPEC:
- Name: {prompt.name}
- File: {prompt.file_name}
- Description: {prompt.description}
- Arguments:
{_format_prompt_arguments(prompt)}

EXACT FILE PATTERN (follow this precisely):

import logging
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.prompts import base

log = logging.getLogger(__name__)

def {register_func}(mcp: FastMCP):
    @mcp.prompt()
    async def {prompt_func}({params_str}) -> list[base.Message]:
        \"\"\"
        {prompt.description}
        \"\"\"
        return [
            base.UserMessage(
                content="A useful prompt template that guides the LLM"
            )
        ]

CRITICAL RULES:
- Import FastMCP EXACTLY as: `from mcp.server.fastmcp import FastMCP` — NEVER `from fastmcp import FastMCP`
- Import prompts as: `from mcp.server.fastmcp.prompts import base`
- Do NOT import dotenv or call load_dotenv()
- Do NOT add any markdown fences or backticks in output
- The register function MUST be named exactly: {register_func}
- The register function takes `mcp: FastMCP` as its only parameter
- Use @mcp.prompt() decorator
- Return list[base.Message] — use base.UserMessage or base.AssistantMessage
- The prompt should guide the LLM to use this server's tools effectively
- Make the prompt genuinely useful as a workflow template
- Use logging, NEVER print()
- Output ONLY the Python code, no markdown"""

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def _build_ts_prompt_prompt(arch: MCPArchitecture, prompt: PromptDefinition) -> list[dict]:
    func_name = _to_register_prompt_func_ts(prompt.name)

    # Build Zod schema entries
    zod_entries = []
    for a in prompt.arguments:
        zod_type = "z.string()" if a.type == "string" else f"z.{a.type}()"
        if not a.required:
            zod_type += ".optional()"
        zod_entries.append(f'      {a.name}: {zod_type}.describe("{a.description}")')
    zod_schema = ",\n".join(zod_entries) if zod_entries else '      // No arguments'

    system = """You are a code generator that produces TypeScript MCP prompt implementation files.
Output ONLY raw TypeScript code. NEVER wrap output in markdown code fences (``` or ```typescript).
No explanation text before or after the code. Just the TypeScript source file content.
The code must be production-ready."""

    user = f"""Generate a complete TypeScript MCP prompt implementation file.

SERVER: {arch.server_name} — {arch.server_description}

AVAILABLE TOOLS (prompts should guide the LLM to use these):
{_format_tools_summary(arch)}

PROMPT SPEC:
- Name: {prompt.name}
- File: {prompt.file_name}
- Description: {prompt.description}
- Arguments:
{_format_prompt_arguments(prompt)}

EXACT FILE PATTERN (follow this precisely):

import {{ McpServer }} from "@modelcontextprotocol/sdk/server/mcp.js";
import {{ z }} from "zod";

export function {func_name}(server: McpServer): void {{
  server.prompt(
    "{prompt.name}",
    "{prompt.description}",
    {{
{zod_schema}
    }},
    async ({{ /* destructured args */ }}) => ({{
      messages: [
        {{
          role: "user",
          content: {{
            type: "text",
            text: "A useful prompt template that guides the LLM"
          }}
        }}
      ]
    }})
  );
}}

CRITICAL RULES:
- Import MUST be: `import {{ McpServer }} from "@modelcontextprotocol/sdk/server/mcp.js";`
- Do NOT add any markdown fences or backticks in output
- The function MUST be named exactly: {func_name}
- Use Zod schemas for ALL prompt arguments with .describe()
- The prompt should guide the LLM to use this server's tools effectively
- Read env vars with process.env.VAR_NAME if needed
- All logging to stderr via console.error()
- Do NOT use console.log() — only console.error()
- Output ONLY the TypeScript code, no markdown"""

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
