import { useCallback, useReducer } from "react";
import { useWebSocket } from "./useWebSocket";
import type {
  ChatMessage,
  ConversationPhase,
  DeploymentInfo,
  MCPArchitecture,
  OptionItem,
  WSFrame,
} from "../types/messages";

interface ChatState {
  messages: ChatMessage[];
  isStreaming: boolean;
  streamingMessageId: string | null;
  streamingText: string;
  currentPhase: ConversationPhase;
  architecture: MCPArchitecture | null;
  pendingOptions: {
    question_id: string;
    question: string;
    options: OptionItem[];
    allow_multiple: boolean;
    allow_freeform: boolean;
  } | null;
  error: string | null;
  isGenerating: boolean;
  generationProgress: { step: string; current: number; total: number } | null;
  downloadUrl: string | null;
  isDeploying: boolean;
  deploymentProgress: { step: string; current: number; total: number } | null;
  deployment: DeploymentInfo | null;
}

type ChatAction =
  | { type: "ADD_USER_MESSAGE"; text: string }
  | { type: "START_STREAMING"; messageId: string }
  | { type: "APPEND_CHUNK"; chunk: string }
  | {
      type: "COMPLETE_MESSAGE";
      messageId: string;
      fullText: string;
      phase: ConversationPhase;
    }
  | { type: "SET_PHASE"; phase: ConversationPhase; message: string }
  | {
      type: "SET_OPTIONS";
      question_id: string;
      question: string;
      options: OptionItem[];
      allow_multiple: boolean;
      allow_freeform: boolean;
    }
  | { type: "CLEAR_OPTIONS" }
  | { type: "SET_ARCHITECTURE"; architecture: MCPArchitecture; summary: string }
  | { type: "START_GENERATION" }
  | { type: "GENERATION_PROGRESS"; step: string; current: number; total: number }
  | { type: "GENERATION_COMPLETE"; downloadUrl: string }
  | { type: "DEPLOYMENT_PROGRESS"; step: string; current: number; total: number }
  | { type: "DEPLOYMENT_COMPLETE"; deployment: DeploymentInfo }
  | { type: "SET_ERROR"; message: string }
  | { type: "CLEAR_ERROR" };

function chatReducer(state: ChatState, action: ChatAction): ChatState {
  switch (action.type) {
    case "ADD_USER_MESSAGE":
      return {
        ...state,
        messages: [
          ...state.messages,
          {
            id: crypto.randomUUID(),
            role: "user",
            content: [{ type: "text", text: action.text }],
            timestamp: new Date().toISOString(),
          },
        ],
        error: null,
      };

    case "START_STREAMING":
      // Idempotent: if already streaming this same message, don't reset
      if (state.isStreaming && state.streamingMessageId === action.messageId) {
        return state;
      }
      return {
        ...state,
        isStreaming: true,
        streamingMessageId: action.messageId,
        streamingText: "",
      };

    case "APPEND_CHUNK":
      return {
        ...state,
        streamingText: state.streamingText + action.chunk,
      };

    case "COMPLETE_MESSAGE": {
      const text = action.fullText || state.streamingText;
      const newMessages = text
        ? [
            ...state.messages,
            {
              id: action.messageId,
              role: "assistant" as const,
              content: [{ type: "text" as const, text }],
              timestamp: new Date().toISOString(),
            },
          ]
        : state.messages;
      return {
        ...state,
        messages: newMessages,
        isStreaming: false,
        streamingMessageId: null,
        streamingText: "",
        currentPhase: action.phase || state.currentPhase,
      };
    }

    case "SET_PHASE":
      return {
        ...state,
        currentPhase: action.phase,
        // Start deploying phase when we get "deploying" phase
        isDeploying: action.phase === ("deploying" as ConversationPhase) ? true : state.isDeploying,
        messages: [
          ...state.messages,
          {
            id: crypto.randomUUID(),
            role: "system",
            content: [
              { type: "progress", phase: action.phase, message: action.message },
            ],
            timestamp: new Date().toISOString(),
          },
        ],
      };

    case "SET_OPTIONS":
      return {
        ...state,
        pendingOptions: {
          question_id: action.question_id,
          question: action.question,
          options: action.options,
          allow_multiple: action.allow_multiple,
          allow_freeform: action.allow_freeform,
        },
      };

    case "CLEAR_OPTIONS":
      return { ...state, pendingOptions: null };

    case "SET_ARCHITECTURE":
      return {
        ...state,
        architecture: action.architecture,
        currentPhase: "complete",
        messages: [
          ...state.messages,
          {
            id: crypto.randomUUID(),
            role: "system",
            content: [
              {
                type: "architecture",
                summary: action.architecture as unknown as Record<string, unknown>,
              },
            ],
            timestamp: new Date().toISOString(),
          },
        ],
      };

    case "START_GENERATION":
      return {
        ...state,
        isGenerating: true,
        generationProgress: null,
        downloadUrl: null,
        deployment: null,
        currentPhase: "generating",
      };

    case "GENERATION_PROGRESS":
      return {
        ...state,
        generationProgress: {
          step: action.step,
          current: action.current,
          total: action.total,
        },
      };

    case "GENERATION_COMPLETE":
      return {
        ...state,
        isGenerating: false,
        downloadUrl: action.downloadUrl,
        generationProgress: null,
        // Don't set phase to complete yet — deployment follows
        isDeploying: true,
        deploymentProgress: null,
      };

    case "DEPLOYMENT_PROGRESS":
      return {
        ...state,
        isDeploying: true,
        deploymentProgress: {
          step: action.step,
          current: action.current,
          total: action.total,
        },
      };

    case "DEPLOYMENT_COMPLETE":
      return {
        ...state,
        isDeploying: false,
        deploymentProgress: null,
        deployment: action.deployment,
        currentPhase: "complete",
      };

    case "SET_ERROR":
      return {
        ...state,
        error: action.message,
        isStreaming: false,
        isGenerating: false,
        isDeploying: false,
        streamingText: "",
      };

    case "CLEAR_ERROR":
      return { ...state, error: null };

    default:
      return state;
  }
}

const initialState: ChatState = {
  messages: [],
  isStreaming: false,
  streamingMessageId: null,
  streamingText: "",
  currentPhase: "initial",
  architecture: null,
  pendingOptions: null,
  error: null,
  isGenerating: false,
  generationProgress: null,
  downloadUrl: null,
  isDeploying: false,
  deploymentProgress: null,
  deployment: null,
};

export function useChat() {
  const [state, dispatch] = useReducer(chatReducer, initialState);

  // Handle every WebSocket frame directly via callback — no state batching, no dropped frames.
  // dispatch from useReducer is stable and processes updates sequentially.
  const handleFrame = useCallback(
    (frame: WSFrame) => {
      const payload = frame.payload;

      switch (frame.type) {
        case "system_message":
          if (payload.phase !== "initial") {
            dispatch({
              type: "SET_PHASE",
              phase: payload.phase as ConversationPhase,
              message: payload.message as string,
            });
          }
          break;

        case "assistant_chunk":
          // Always dispatch both — the reducer handles START_STREAMING idempotently
          dispatch({
            type: "START_STREAMING",
            messageId: payload.message_id as string,
          });
          dispatch({ type: "APPEND_CHUNK", chunk: payload.chunk as string });
          break;

        case "assistant_complete":
          dispatch({
            type: "COMPLETE_MESSAGE",
            messageId: payload.message_id as string,
            fullText: payload.full_text as string,
            phase: payload.phase as ConversationPhase,
          });
          break;

        case "options_prompt":
          dispatch({
            type: "SET_OPTIONS",
            question_id: payload.question_id as string,
            question: payload.question as string,
            options: payload.options as OptionItem[],
            allow_multiple: payload.allow_multiple as boolean,
            allow_freeform: payload.allow_freeform as boolean,
          });
          break;

        case "architecture_ready":
          dispatch({
            type: "SET_ARCHITECTURE",
            architecture: payload.architecture as MCPArchitecture,
            summary: payload.summary_text as string,
          });
          break;

        case "generation_progress":
          dispatch({
            type: "GENERATION_PROGRESS",
            step: payload.step as string,
            current: payload.current as number,
            total: payload.total as number,
          });
          break;

        case "generation_complete":
          dispatch({
            type: "GENERATION_COMPLETE",
            downloadUrl: payload.download_url as string,
          });
          break;

        case "deployment_progress":
          dispatch({
            type: "DEPLOYMENT_PROGRESS",
            step: payload.step as string,
            current: payload.current as number,
            total: payload.total as number,
          });
          break;

        case "deployment_complete":
          dispatch({
            type: "DEPLOYMENT_COMPLETE",
            deployment: {
              status: payload.status as "running" | "failed",
              server_url: payload.server_url as string | undefined,
              sse_url: payload.sse_url as string | undefined,
              port: payload.port as number | undefined,
              client_config: payload.client_config as Record<string, unknown> | undefined,
              client_config_json: payload.client_config_json as string | undefined,
              claude_desktop_config: payload.claude_desktop_config as string | undefined,
              cursor_config: payload.cursor_config as string | undefined,
              generic_config: payload.generic_config as string | undefined,
              error: payload.error as string | undefined,
            },
          });
          break;

        case "error":
          dispatch({
            type: "SET_ERROR",
            message: payload.message as string,
          });
          break;
      }
    },
    [] // dispatch is stable from useReducer
  );

  const { isConnected, sessionId, sendFrame } = useWebSocket(handleFrame);

  const sendMessage = useCallback(
    (text: string) => {
      if (!sessionId || !text.trim()) return;
      dispatch({ type: "ADD_USER_MESSAGE", text });
      sendFrame({
        type: "user_message",
        session_id: sessionId,
        payload: { text },
      });
    },
    [sessionId, sendFrame]
  );

  const generateCode = useCallback(
    (envVars?: Record<string, string>) => {
      if (!sessionId) return;
      dispatch({ type: "START_GENERATION" });
      sendFrame({
        type: "generate_code",
        session_id: sessionId,
        payload: envVars ? { env_vars: envVars } : {},
      });
    },
    [sessionId, sendFrame]
  );

  const selectOption = useCallback(
    (questionId: string, selectedOptions: string[], freeformText?: string) => {
      if (!sessionId) return;
      const displayText = freeformText || selectedOptions.join(", ");
      dispatch({ type: "ADD_USER_MESSAGE", text: displayText });
      dispatch({ type: "CLEAR_OPTIONS" });
      sendFrame({
        type: "option_selected",
        session_id: sessionId,
        payload: {
          question_id: questionId,
          selected_options: selectedOptions,
          freeform_text: freeformText || null,
        },
      });
    },
    [sessionId, sendFrame]
  );

  return {
    messages: state.messages,
    isStreaming: state.isStreaming,
    streamingText: state.streamingText,
    currentPhase: state.currentPhase,
    architecture: state.architecture,
    pendingOptions: state.pendingOptions,
    error: state.error,
    isConnected,
    sessionId,
    sendMessage,
    selectOption,
    generateCode,
    isGenerating: state.isGenerating,
    generationProgress: state.generationProgress,
    downloadUrl: state.downloadUrl,
    isDeploying: state.isDeploying,
    deploymentProgress: state.deploymentProgress,
    deployment: state.deployment,
  };
}
