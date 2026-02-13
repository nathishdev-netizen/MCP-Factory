import ReactMarkdown from "react-markdown";
import type { ChatMessage } from "../../types/messages";

interface MessageBubbleProps {
  message: ChatMessage;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const { role, content } = message;

  return (
    <div className={`message-bubble ${role}`}>
      <div className="message-avatar">
        {role === "user" ? "You" : role === "assistant" ? "AI" : "Sys"}
      </div>
      <div className="message-content">
        {content.map((block, i) => {
          switch (block.type) {
            case "text":
              return (
                <div key={i} className="message-text markdown-body">
                  {role === "assistant" ? (
                    <ReactMarkdown>{block.text}</ReactMarkdown>
                  ) : (
                    block.text
                  )}
                </div>
              );
            case "progress":
              return (
                <div key={i} className="message-progress">
                  <span className="progress-dot" />
                  {block.message}
                </div>
              );
            case "architecture":
              return (
                <div key={i} className="architecture-card">
                  <ArchitectureSummary data={block.summary} />
                </div>
              );
            default:
              return null;
          }
        })}
      </div>
    </div>
  );
}

function ArchitectureSummary({ data }: { data: Record<string, unknown> }) {
  const arch = data as {
    server_name?: string;
    server_description?: string;
    language?: string;
    tools?: { name: string; description: string }[];
    env_vars?: { name: string; description: string }[];
    extra_dependencies?: { package: string; reason: string }[];
  };

  return (
    <div className="architecture-summary">
      <h3>MCP Server Architecture</h3>
      <div className="arch-field">
        <span className="arch-label">Name:</span>
        <span className="arch-value">{arch.server_name}</span>
      </div>
      <div className="arch-field">
        <span className="arch-label">Description:</span>
        <span className="arch-value">{arch.server_description}</span>
      </div>
      <div className="arch-field">
        <span className="arch-label">Language:</span>
        <span className="arch-value lang-badge">{arch.language}</span>
      </div>

      {arch.tools && arch.tools.length > 0 && (
        <div className="arch-section">
          <h4>Tools ({arch.tools.length})</h4>
          <ul className="tool-list">
            {arch.tools.map((tool) => (
              <li key={tool.name} className="tool-item">
                <code>{tool.name}</code>
                <span>{tool.description}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {arch.env_vars && arch.env_vars.length > 0 && (
        <div className="arch-section">
          <h4>Environment Variables</h4>
          <ul className="env-list">
            {arch.env_vars.map((env) => (
              <li key={env.name}>
                <code>{env.name}</code> - {env.description}
              </li>
            ))}
          </ul>
        </div>
      )}

      {arch.extra_dependencies && arch.extra_dependencies.length > 0 && (
        <div className="arch-section">
          <h4>Dependencies</h4>
          <ul className="dep-list">
            {arch.extra_dependencies.map((dep) => (
              <li key={dep.package}>
                <code>{dep.package}</code> - {dep.reason}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
