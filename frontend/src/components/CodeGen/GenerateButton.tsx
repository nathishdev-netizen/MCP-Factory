import { useState } from "react";

interface EnvVarDef {
  name: string;
  description: string;
  required: boolean;
  example: string;
}

interface GenerateButtonProps {
  onClick: (envVars?: Record<string, string>) => void;
  envVars?: EnvVarDef[];
}

export function GenerateButton({ onClick, envVars }: GenerateButtonProps) {
  const [values, setValues] = useState<Record<string, string>>({});
  const hasEnvVars = envVars && envVars.length > 0;

  const handleChange = (name: string, value: string) => {
    setValues((prev) => ({ ...prev, [name]: value }));
  };

  const handleGenerate = () => {
    const filled: Record<string, string> = {};
    if (hasEnvVars) {
      for (const env of envVars) {
        if (values[env.name]?.trim()) {
          filled[env.name] = values[env.name].trim();
        }
      }
    }
    onClick(Object.keys(filled).length > 0 ? filled : undefined);
  };

  return (
    <div className="generate-button-container">
      {hasEnvVars && (
        <div className="env-vars-form">
          <h4 className="env-vars-title">Environment Variables</h4>
          <p className="env-vars-hint">
            Enter your credentials now to auto-configure the deployed server, or
            leave blank to use placeholders (you can update them later).
          </p>
          <div className="env-vars-fields">
            {envVars.map((env) => (
              <div key={env.name} className="env-var-field">
                <label className="env-var-label">
                  <code>{env.name}</code>
                  {env.required && <span className="env-required">*</span>}
                </label>
                <p className="env-var-desc">{env.description}</p>
                <input
                  type={
                    env.name.toLowerCase().includes("password") ||
                    env.name.toLowerCase().includes("token") ||
                    env.name.toLowerCase().includes("secret") ||
                    env.name.toLowerCase().includes("key")
                      ? "password"
                      : "text"
                  }
                  className="env-var-input"
                  placeholder={env.example || `Enter ${env.name}...`}
                  value={values[env.name] || ""}
                  onChange={(e) => handleChange(env.name, e.target.value)}
                />
              </div>
            ))}
          </div>
        </div>
      )}

      <p className="generate-description">
        {hasEnvVars
          ? "Ready to generate! Credentials are optional \u2014 you can add them later."
          : "Your architecture is ready! Click below to generate the complete MCP server project."}
      </p>
      <button className="generate-button" onClick={handleGenerate}>
        <svg
          width="18"
          height="18"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <polyline points="16 18 22 12 16 6" />
          <polyline points="8 6 2 12 8 18" />
        </svg>
        Generate Code
      </button>
    </div>
  );
}
