from __future__ import annotations

import json

from app.models.architecture import (
    MCPArchitecture,
    ToolDefinition,
    ToolParameter,
    ToolAnnotations,
    ResourceDefinition,
    PromptDefinition,
    Dependency,
    EnvVar,
    AuthSetup,
)


def _coerce_tool_param(p: dict) -> ToolParameter:
    """Coerce LLM-returned parameter values to the types ToolParameter expects."""
    raw = dict(p)  # shallow copy
    # default: LLM may return int/float/bool/list — stringify them
    if "default" in raw and raw["default"] is not None and not isinstance(raw["default"], str):
        raw["default"] = json.dumps(raw["default"]) if isinstance(raw["default"], (dict, list)) else str(raw["default"])
    # validation: LLM may return a dict like {"minimum": 1, "maximum": 100} — stringify it
    if "validation" in raw and raw["validation"] is not None and not isinstance(raw["validation"], str):
        raw["validation"] = json.dumps(raw["validation"]) if isinstance(raw["validation"], (dict, list)) else str(raw["validation"])
    # enum_values: ensure every element is a string
    if "enum_values" in raw and isinstance(raw["enum_values"], list):
        raw["enum_values"] = [str(v) for v in raw["enum_values"]]
    return ToolParameter(**raw)


def parse_architecture_response(data: dict) -> MCPArchitecture:
    """Parse the JSON output from the architecture phase into MCPArchitecture."""
    tools = []
    for t in data.get("tools", []):
        params = [_coerce_tool_param(p) for p in t.get("parameters", [])]
        annotations = ToolAnnotations(**(t.get("annotations", {})))
        tools.append(
            ToolDefinition(
                name=t["name"],
                file_name=t.get("file_name", t["name"].replace(".", "_") + ".py"),
                description=t.get("description", ""),
                parameters=params,
                return_description=t.get("return_description", ""),
                annotations=annotations,
                external_api=t.get("external_api"),
                error_scenarios=t.get("error_scenarios", []),
            )
        )

    language = data.get("language", "python")

    resources = []
    for r in data.get("resources", []):
        res_name = r.get("name", "resource")
        if not r.get("file_name"):
            # Auto-generate file_name from resource name
            slug = res_name.lower().replace(" ", "_").replace("-", "_")
            r["file_name"] = f"{slug}.py" if language == "python" else f"{slug.replace('_', '-')}.ts"
        resources.append(ResourceDefinition(**r))

    prompts = []
    for p in data.get("prompts", []):
        prompt_name = p.get("name", "prompt")
        if not p.get("file_name"):
            # Auto-generate file_name from prompt name
            slug = prompt_name.lower().replace(" ", "_").replace("-", "_")
            p["file_name"] = f"{slug}.py" if language == "python" else f"{slug.replace('_', '-')}.ts"
        prompts.append(
            PromptDefinition(
                name=p["name"],
                file_name=p.get("file_name", ""),
                description=p.get("description", ""),
                arguments=[_coerce_tool_param(a) for a in p.get("arguments", [])],
            )
        )

    dependencies = [
        Dependency(**d) for d in data.get("extra_dependencies", [])
    ]

    env_vars = [
        EnvVar(**e) for e in data.get("env_vars", [])
    ]

    auth = None
    if data.get("auth_setup"):
        auth = AuthSetup(**data["auth_setup"])

    return MCPArchitecture(
        server_name=data.get("server_name", "unnamed-server"),
        server_description=data.get("server_description", ""),
        server_version=data.get("server_version", "1.0.0"),
        server_instructions=data.get("server_instructions", ""),
        language=language,
        language_reasoning=data.get("language_reasoning", ""),
        enable_tools=data.get("enable_tools", True),
        enable_resources=data.get("enable_resources", False),
        enable_prompts=data.get("enable_prompts", False),
        tools=tools,
        resources=resources,
        prompts=prompts,
        extra_dependencies=dependencies,
        env_vars=env_vars,
        auth_setup=auth,
    )
