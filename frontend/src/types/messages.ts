// -- Message types matching backend Pydantic models --

export type MessageRole = "user" | "assistant" | "system";

export type ConversationPhase =
  | "initial"
  | "understanding"
  | "clarifying"
  | "designing"
  | "complete"
  | "generating"
  | "deploying";

// Content types
export interface TextContent {
  type: "text";
  text: string;
}

export interface OptionItem {
  id: string;
  label: string;
  description?: string;
}

export interface OptionsContent {
  type: "options";
  question: string;
  question_id: string;
  options: OptionItem[];
  allow_multiple: boolean;
  allow_freeform: boolean;
}

export interface ProgressContent {
  type: "progress";
  phase: ConversationPhase;
  message: string;
}

export interface ArchitectureContent {
  type: "architecture";
  summary: Record<string, unknown>;
}

export type ContentBlock =
  | TextContent
  | OptionsContent
  | ProgressContent
  | ArchitectureContent;

// Chat message
export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: ContentBlock[];
  timestamp: string;
}

// WebSocket protocol
export type WSMessageType =
  | "user_message"
  | "option_selected"
  | "generate_code"
  | "assistant_chunk"
  | "assistant_complete"
  | "system_message"
  | "options_prompt"
  | "architecture_ready"
  | "generation_progress"
  | "generation_complete"
  | "deployment_progress"
  | "deployment_complete"
  | "error";

export interface WSFrame {
  type: WSMessageType;
  session_id: string;
  payload: Record<string, unknown>;
  timestamp: string;
}

// Architecture types (for display)
export interface ToolDefinition {
  name: string;
  file_name: string;
  description: string;
  parameters: ToolParameter[];
  return_description: string;
  annotations: {
    read_only_hint: boolean;
    destructive_hint: boolean;
    idempotent_hint: boolean;
    open_world_hint: boolean;
  };
  external_api?: string;
  error_scenarios: string[];
}

export interface ToolParameter {
  name: string;
  type: string;
  description: string;
  required: boolean;
  default?: string;
  enum_values?: string[];
}

export interface MCPArchitecture {
  server_name: string;
  server_description: string;
  server_version: string;
  language: string;
  language_reasoning: string;
  enable_tools: boolean;
  enable_resources: boolean;
  enable_prompts: boolean;
  tools: ToolDefinition[];
  extra_dependencies: { package: string; reason: string }[];
  env_vars: { name: string; description: string; required: boolean; example: string }[];
  auth_setup?: {
    type: string;
    description: string;
    env_var_names: string[];
  };
}

// Deployment info
export interface DeploymentInfo {
  status: "running" | "failed";
  server_url?: string;
  sse_url?: string;
  port?: number;
  client_config?: Record<string, unknown>;
  client_config_json?: string;
  claude_desktop_config?: string;
  cursor_config?: string;
  generic_config?: string;
  error?: string;
}
