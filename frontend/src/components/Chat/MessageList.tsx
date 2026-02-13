import { useEffect, useRef } from "react";
import type { ChatMessage } from "../../types/messages";
import { MessageBubble } from "./MessageBubble";
import { StreamingText } from "./StreamingText";

interface MessageListProps {
  messages: ChatMessage[];
  isStreaming: boolean;
  streamingText: string;
  onSendPrompt?: (text: string) => void;
}

export function MessageList({ messages, isStreaming, streamingText, onSendPrompt }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingText]);

  return (
    <div className="message-list">
      {messages.length === 0 && !isStreaming && (
        <div className="welcome-message">
          <div className="welcome-icon">
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none">
              <rect x="2" y="2" width="20" height="20" rx="4" stroke="currentColor" strokeWidth="1.5" />
              <path d="M7 8h4M7 12h10M7 16h7" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
              <circle cx="18" cy="8" r="2" fill="currentColor" />
            </svg>
          </div>
          <h2>Welcome to MCP Factory</h2>
          <p>
            Describe what you need, and I'll design a custom MCP server for you.
          </p>
          <div className="example-prompts">
            <p>Try something like:</p>
            <ul>
              <li onClick={() => onSendPrompt?.("I need an MCP server that manages GitHub issues and sends Slack notifications")}>
                I need an MCP server that manages GitHub issues and sends Slack notifications
              </li>
              <li onClick={() => onSendPrompt?.("Build me an MCP that searches for hotels and compares prices")}>
                Build me an MCP that searches for hotels and compares prices
              </li>
              <li onClick={() => onSendPrompt?.("I want to automate email workflows with Gmail and Google Calendar")}>
                I want to automate email workflows with Gmail and Google Calendar
              </li>
            </ul>
          </div>
        </div>
      )}

      {messages.map((msg) => (
        <MessageBubble key={msg.id} message={msg} />
      ))}

      {isStreaming && streamingText && <StreamingText text={streamingText} />}

      <div ref={bottomRef} />
    </div>
  );
}
