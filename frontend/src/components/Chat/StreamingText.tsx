interface StreamingTextProps {
  text: string;
}

export function StreamingText({ text }: StreamingTextProps) {
  return (
    <div className="message-bubble assistant">
      <div className="message-avatar">AI</div>
      <div className="message-content">
        <div className="message-text streaming">
          {text}
          <span className="cursor-blink">|</span>
        </div>
      </div>
    </div>
  );
}
