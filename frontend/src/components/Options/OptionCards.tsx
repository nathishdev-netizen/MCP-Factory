import { useState } from "react";
import type { OptionItem } from "../../types/messages";

interface OptionCardsProps {
  questionId: string;
  question: string;
  options: OptionItem[];
  allowFreeform: boolean;
  onSelect: (questionId: string, selected: string[], freeform?: string) => void;
}

export function OptionCards({
  questionId,
  question,
  options,
  allowFreeform,
  onSelect,
}: OptionCardsProps) {
  const [freeformText, setFreeformText] = useState("");
  const [showFreeform, setShowFreeform] = useState(false);

  return (
    <div className="option-cards-wrapper">
      <p className="option-question">{question}</p>
      <div className="option-cards">
        {options.map((opt) => (
          <button
            key={opt.id}
            className="option-card"
            onClick={() => onSelect(questionId, [opt.label])}
          >
            <span className="option-label">{opt.label}</span>
            {opt.description && (
              <span className="option-description">{opt.description}</span>
            )}
          </button>
        ))}
      </div>

      {allowFreeform && (
        <div className="freeform-option">
          {showFreeform ? (
            <div className="freeform-input-wrapper">
              <input
                type="text"
                className="freeform-input"
                value={freeformText}
                onChange={(e) => setFreeformText(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && freeformText.trim()) {
                    onSelect(questionId, [], freeformText.trim());
                  }
                }}
                placeholder="Type your answer..."
                autoFocus
              />
              <button
                className="freeform-send"
                onClick={() => {
                  if (freeformText.trim()) {
                    onSelect(questionId, [], freeformText.trim());
                  }
                }}
                disabled={!freeformText.trim()}
              >
                Send
              </button>
            </div>
          ) : (
            <button
              className="show-freeform-btn"
              onClick={() => setShowFreeform(true)}
            >
              Or type your own answer...
            </button>
          )}
        </div>
      )}
    </div>
  );
}
