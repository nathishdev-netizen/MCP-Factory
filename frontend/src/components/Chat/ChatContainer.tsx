import { useChat } from "../../hooks/useChat";
import { Header } from "../Layout/Header";
import { PhaseIndicator } from "../Progress/PhaseIndicator";
import { MessageList } from "./MessageList";
import { ChatInput } from "./ChatInput";
import { OptionCards } from "../Options/OptionCards";
import { GenerateButton } from "../CodeGen/GenerateButton";
import { GenerationProgress } from "../CodeGen/GenerationProgress";
import { DeploymentCard } from "../CodeGen/DeploymentCard";

export function ChatContainer() {
  const {
    messages,
    isStreaming,
    streamingText,
    currentPhase,
    architecture,
    pendingOptions,
    error,
    isConnected,
    sendMessage,
    selectOption,
    generateCode,
    isGenerating,
    generationProgress,
    downloadUrl,
    isDeploying,
    deploymentProgress,
    deployment,
    sessionId,
  } = useChat();

  const inputDisabled =
    !isConnected || isStreaming || isGenerating || isDeploying || !!deployment;

  return (
    <div className="chat-container">
      <Header isConnected={isConnected} currentPhase={currentPhase} />
      <PhaseIndicator currentPhase={currentPhase} />

      <div className="chat-body">
        <MessageList
          messages={messages}
          isStreaming={isStreaming}
          streamingText={streamingText}
          onSendPrompt={sendMessage}
        />

        {pendingOptions && (
          <OptionCards
            questionId={pendingOptions.question_id}
            question={pendingOptions.question}
            options={pendingOptions.options}
            allowFreeform={pendingOptions.allow_freeform}
            onSelect={selectOption}
          />
        )}

        {architecture && !isGenerating && !isDeploying && !downloadUrl && !deployment && (
          <GenerateButton
            onClick={generateCode}
            envVars={architecture.env_vars}
          />
        )}

        {isGenerating && generationProgress && (
          <GenerationProgress
            currentStep={generationProgress.step}
            currentIndex={generationProgress.current}
            totalSteps={generationProgress.total}
          />
        )}

        {isDeploying && (
          <div className="generation-progress">
            <div className="progress-header">
              <span className="progress-spinner" />
              <span>Deploying your MCP server...</span>
            </div>
            {deploymentProgress && (
              <>
                <div className="progress-bar-track">
                  <div
                    className="progress-bar-fill deployment-bar"
                    style={{
                      width: `${Math.round(
                        (deploymentProgress.current / deploymentProgress.total) * 100
                      )}%`,
                    }}
                  />
                </div>
                <div className="progress-detail">
                  <span className="progress-step-name">
                    {deploymentProgress.step}
                  </span>
                  <span className="progress-step-count">
                    {deploymentProgress.current} / {deploymentProgress.total}
                  </span>
                </div>
              </>
            )}
          </div>
        )}

        {deployment && architecture && (
          <DeploymentCard
            deployment={deployment}
            serverName={architecture.server_name}
            downloadUrl={downloadUrl}
            sessionId={sessionId || ""}
          />
        )}

        {error && (
          <div className="error-banner">
            <span>{error}</span>
          </div>
        )}
      </div>

      <ChatInput
        onSend={sendMessage}
        disabled={inputDisabled}
        placeholder={
          deployment
            ? "Your MCP server is live! Connect using the config above."
            : isDeploying
            ? "Deploying server..."
            : isGenerating
            ? "Generating code..."
            : currentPhase === "complete"
            ? "Architecture ready — click Generate Code above"
            : isStreaming
            ? "AI is thinking..."
            : "Describe what MCP server you need..."
        }
      />
    </div>
  );
}
