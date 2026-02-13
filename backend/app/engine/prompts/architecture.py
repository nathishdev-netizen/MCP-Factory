ARCHITECTURE_PROMPT_TEMPLATE = """CURRENT PHASE: ARCHITECTURE DESIGN

You have gathered complete requirements. Now design the full MCP server architecture.

GATHERED REQUIREMENTS:
{requirements}

Design a complete MCP server. After your natural language summary, output JSON with this schema:

---JSON---
{{
  "server_name": "snake-case-name (must match ^[a-z][a-z0-9_-]{{1,50}}$)",
  "server_description": "One clear sentence (max 200 chars)",
  "server_version": "1.0.0",
  "server_instructions": "Instructions for the LLM on how to use this server's tools",
  "language": "typescript|python",
  "language_reasoning": "Why this language was chosen",
  "enable_tools": true,
  "enable_resources": true or false,
  "enable_prompts": true or false,
  "tools": [
    {{
      "name": "snake_case.name",
      "file_name": "kebab-case.ts or snake_case.py",
      "description": "What this tool does",
      "parameters": [
        {{
          "name": "param_name",
          "type": "string|number|boolean|array|object",
          "description": "What this param is",
          "required": true,
          "default": null,
          "enum_values": null,
          "validation": null
        }}
      ],
      "return_description": "What this tool returns",
      "annotations": {{
        "read_only_hint": false,
        "destructive_hint": false,
        "idempotent_hint": false,
        "open_world_hint": true
      }},
      "external_api": "Which API this calls or null",
      "error_scenarios": ["What can go wrong"]
    }}
  ],
  "resources": [
    {{
      "uri_template": "resource://server-name/resource-path/{{id}}",
      "name": "Descriptive resource name",
      "file_name": "kebab-case.ts or snake_case.py (one file per resource)",
      "description": "What data this resource exposes",
      "mime_type": "application/json"
    }}
  ],
  "prompts": [
    {{
      "name": "prompt-name",
      "file_name": "kebab-case.ts or snake_case.py (one file per prompt)",
      "description": "What this prompt template does",
      "arguments": [
        {{
          "name": "arg_name",
          "type": "string",
          "description": "What this argument is",
          "required": true
        }}
      ]
    }}
  ],
  "extra_dependencies": [
    {{"package": "package-name>=1.0.0", "reason": "Why needed"}}
  ],
  "env_vars": [
    {{"name": "ENV_VAR_NAME", "description": "What it is and how to get it (e.g. 'GitHub PAT — create at github.com > Settings > Developer settings > Personal access tokens, select repo scope')", "required": true, "example": "ghp_xxxxxxxxxxxx"}}
  ],
  "auth_setup": {{
    "type": "api_key|oauth2|basic|none",
    "description": "How auth works",
    "env_var_names": ["RELATED_ENV_VARS"]
  }}
}}

CONSTRAINTS:
- Max 25 tools
- One tool per file
- Tool names: snake_case with optional dot namespace (e.g., issues.create, issues.list)
- File names: kebab-case.ts for TypeScript, snake_case.py for Python
- Every tool must have error handling, input validation, annotations
- readOnlyHint=true for GET-like tools, destructiveHint=true for DELETE/destructive tools
- idempotentHint=true for PUT-like idempotent operations
- Use env vars for all secrets and API keys, never hardcode
- Each env_var description MUST include: what it is, why it's needed, and step-by-step instructions on how to obtain it (e.g. which settings page to visit, what scopes to select). Use the example field to show the expected format (e.g. "ghp_xxxx", "postgresql://user:pass@host/db")
- Include realistic error scenarios for each tool

RESOURCES — Design resources that expose data the LLM can read:
- Resources are READ-ONLY data endpoints accessed via URI templates (MCP spec)
- One resource per file — same pattern as tools
- File names: kebab-case.ts for TypeScript, snake_case.py for Python
- URI templates: use "resource://server-name/path" for static, "resource://server-name/path/{{id}}" for dynamic
- Good examples: "config://server/settings", "data://todos/{{id}}", "stats://server/health"
- Design 1-3 resources that complement the tools (e.g., list view, single item, server status)
- Set enable_resources=true if you include any resources
- If the server has no meaningful data to expose as resources, use an empty array

PROMPTS — Design prompt templates that help the LLM use the server:
- Prompts are user-controlled reusable templates (MCP spec: user picks which prompt to invoke)
- One prompt per file — same pattern as tools
- File names: kebab-case.ts for TypeScript, snake_case.py for Python
- Good examples: "summarize-todos", "create-from-description", "daily-report", "bulk-action"
- Design 1-3 prompts that guide the LLM to use the server's tools effectively
- Each prompt should have arguments that customize its behavior
- Set enable_prompts=true if you include any prompts
- ALWAYS include at least 1 prompt — every server benefits from at least a "help" or "guide" prompt

YOUR TEXT RESPONSE (shown to the user in chat):
Write a clear, friendly summary of the architecture you've designed. Structure it like:
1. A brief intro sentence (e.g., "Here's the architecture for your Weather MCP server!")
2. **Server overview** — name, language, and what it does in 1-2 sentences
3. **Tools** — list each tool with its name in bold and a short description
4. **Resources** — list any resources with their URI and what data they expose
5. **Prompts** — list prompt templates and what they help with
6. **Authentication** — how auth works and what env vars are needed
7. **Dependencies** — key packages being used
Keep it conversational and easy to scan. Use markdown formatting (bold, bullet lists).
"""


def build_architecture_prompt(requirements_json: str) -> str:
    return ARCHITECTURE_PROMPT_TEMPLATE.format(requirements=requirements_json)
