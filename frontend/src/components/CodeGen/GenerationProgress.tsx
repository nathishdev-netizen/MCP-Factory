interface GenerationProgressProps {
  currentStep: string;
  currentIndex: number;
  totalSteps: number;
}

export function GenerationProgress({
  currentStep,
  currentIndex,
  totalSteps,
}: GenerationProgressProps) {
  const percent = Math.round((currentIndex / totalSteps) * 100);

  return (
    <div className="generation-progress">
      <div className="progress-header">
        <span className="progress-spinner" />
        <span>Generating your MCP server...</span>
      </div>
      <div className="progress-bar-track">
        <div
          className="progress-bar-fill"
          style={{ width: `${percent}%` }}
        />
      </div>
      <div className="progress-detail">
        <span className="progress-step-name">{currentStep}</span>
        <span className="progress-step-count">
          {currentIndex} / {totalSteps}
        </span>
      </div>
    </div>
  );
}
