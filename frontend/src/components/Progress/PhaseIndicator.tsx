import type { ConversationPhase } from "../../types/messages";

interface PhaseIndicatorProps {
  currentPhase: ConversationPhase;
}

const PHASES: { key: ConversationPhase; label: string }[] = [
  { key: "understanding", label: "Understanding" },
  { key: "clarifying", label: "Clarifying" },
  { key: "designing", label: "Designing" },
  { key: "generating", label: "Generating" },
  { key: "deploying", label: "Deploying" },
  { key: "complete", label: "Complete" },
];

export function PhaseIndicator({ currentPhase }: PhaseIndicatorProps) {
  if (currentPhase === "initial") return null;

  const currentIndex = PHASES.findIndex((p) => p.key === currentPhase);

  return (
    <div className="phase-indicator">
      {PHASES.map((phase, index) => {
        let status: "done" | "active" | "pending" = "pending";
        if (index < currentIndex) status = "done";
        else if (index === currentIndex) status = "active";

        return (
          <div key={phase.key} className="phase-step-wrapper">
            <div className={`phase-step ${status}`}>
              <div className="phase-dot">
                {status === "done" ? (
                  <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                    <path d="M2 6L5 9L10 3" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                ) : (
                  <span>{index + 1}</span>
                )}
              </div>
              <span className="phase-label">{phase.label}</span>
            </div>
            {index < PHASES.length - 1 && (
              <div className={`phase-connector ${index < currentIndex ? "done" : ""}`} />
            )}
          </div>
        );
      })}
    </div>
  );
}
