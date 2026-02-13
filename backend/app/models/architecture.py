from __future__ import annotations

from pydantic import BaseModel, Field


class ToolParameter(BaseModel):
    name: str
    type: str  # string, number, boolean, array, object
    description: str
    required: bool = True
    default: str | None = None
    enum_values: list[str] | None = None
    validation: str | None = None


class ToolAnnotations(BaseModel):
    read_only_hint: bool = False
    destructive_hint: bool = False
    idempotent_hint: bool = False
    open_world_hint: bool = True


class ToolDefinition(BaseModel):
    name: str
    file_name: str
    description: str
    parameters: list[ToolParameter]
    return_description: str
    annotations: ToolAnnotations = Field(default_factory=ToolAnnotations)
    external_api: str | None = None
    error_scenarios: list[str] = Field(default_factory=list)


class ResourceDefinition(BaseModel):
    uri_template: str
    name: str
    file_name: str = ""
    description: str
    mime_type: str = "application/json"


class PromptDefinition(BaseModel):
    name: str
    file_name: str = ""
    description: str
    arguments: list[ToolParameter] = Field(default_factory=list)


class Dependency(BaseModel):
    package: str
    reason: str


class EnvVar(BaseModel):
    name: str
    description: str
    required: bool = True
    example: str = ""


class AuthSetup(BaseModel):
    type: str  # api_key, oauth2, basic, none
    description: str
    env_var_names: list[str] = Field(default_factory=list)


class MCPArchitecture(BaseModel):
    server_name: str
    server_description: str
    server_version: str = "1.0.0"
    server_instructions: str = ""

    language: str  # typescript | python
    language_reasoning: str = ""

    enable_tools: bool = True
    enable_resources: bool = False
    enable_prompts: bool = False

    tools: list[ToolDefinition] = Field(default_factory=list)
    resources: list[ResourceDefinition] = Field(default_factory=list)
    prompts: list[PromptDefinition] = Field(default_factory=list)

    extra_dependencies: list[Dependency] = Field(default_factory=list)
    env_vars: list[EnvVar] = Field(default_factory=list)
    auth_setup: AuthSetup | None = None
