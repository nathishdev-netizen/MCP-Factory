interface DownloadCardProps {
  serverName: string;
  language: string;
  toolCount: number;
  downloadUrl: string;
}

export function DownloadCard({
  serverName,
  language,
  toolCount,
  downloadUrl,
}: DownloadCardProps) {
  return (
    <div className="download-card">
      <div className="download-card-header">
        <svg
          width="28"
          height="28"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
          <polyline points="7 10 12 15 17 10" />
          <line x1="12" y1="15" x2="12" y2="3" />
        </svg>
        <h3>Your MCP Server is Ready!</h3>
      </div>
      <div className="download-meta">
        <span>
          <strong>Name:</strong> {serverName}
        </span>
        <span>
          <strong>Language:</strong>{" "}
          <span className="lang-badge">{language}</span>
        </span>
        <span>
          <strong>Tools:</strong> {toolCount}
        </span>
      </div>
      <a href={downloadUrl} className="download-button" download>
        <svg
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
          <polyline points="7 10 12 15 17 10" />
          <line x1="12" y1="15" x2="12" y2="3" />
        </svg>
        Download ZIP
      </a>
    </div>
  );
}
