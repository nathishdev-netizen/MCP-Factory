import type { ConversationPhase } from "../../types/messages";

interface HeaderProps {
  isConnected: boolean;
  currentPhase: ConversationPhase;
}

export function Header({ isConnected, currentPhase }: HeaderProps) {
  return (
    <header className="header">
      <div className="header-left">
        <div className="header-logo">
          <svg width="26" height="26" viewBox="0 0 24 24" fill="none">
            <rect x="2" y="2" width="20" height="20" rx="4" stroke="currentColor" strokeWidth="1.5" />
            <path d="M7 8h4M7 12h10M7 16h7" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
            <circle cx="18" cy="8" r="2" fill="currentColor" />
          </svg>
        </div>
        <div className="header-titles">
          <h1 className="header-title">MCP Factory</h1>
          <span className="header-subtitle">AI-Powered MCP Server Generator</span>
        </div>
      </div>
      <div className="header-right">
        <div className="connection-indicator">
          <span className={`connection-dot ${isConnected ? "connected" : "disconnected"}`} />
          <span className="connection-text">
            {isConnected ? "Connected" : "Reconnecting..."}
          </span>
        </div>
        {currentPhase !== "initial" && (
          <span className="phase-badge">{currentPhase}</span>
        )}
      </div>
    </header>
  );
}
