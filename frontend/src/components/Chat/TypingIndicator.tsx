export function TypingIndicator() {
  return (
    <div className="message-bubble assistant">
      <div className="message-avatar">AI</div>
      <div className="message-content">
        <div className="typing-indicator">
          <span className="typing-dot" />
          <span className="typing-dot" />
          <span className="typing-dot" />
        </div>
      </div>
    </div>
  );
}
