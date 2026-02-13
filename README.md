<div align="center">

# MCP Factory

### Describe it. Generate it. Deploy it. Connect it.

**The AI-powered platform that turns natural language into production-ready MCP servers — in under 60 seconds.**

[Get Started](#-quick-start) | [How It Works](#-how-it-works) | [Architecture](#-architecture) | [Supported Providers](#-supported-llm-providers)

---

<img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white" />
<img src="https://img.shields.io/badge/React-19-61DAFB?style=for-the-badge&logo=react&logoColor=black" />
<img src="https://img.shields.io/badge/FastAPI-0.115+-009688?style=for-the-badge&logo=fastapi&logoColor=white" />
<img src="https://img.shields.io/badge/MCP-1.26+-blueviolet?style=for-the-badge" />
<img src="https://img.shields.io/badge/TypeScript-5.9-3178C6?style=for-the-badge&logo=typescript&logoColor=white" />

</div>

---

## What is MCP Factory?

**MCP Factory** is a full-stack platform that generates complete, production-ready [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) servers from a simple chat conversation.

Instead of writing boilerplate, configuring SDKs, and wiring up transports manually — you just **describe what you need**, and MCP Factory:

1. **Understands** your requirements through an intelligent conversation
2. **Designs** a complete server architecture (tools, resources, prompts, auth, dependencies)
3. **Generates** production-quality code via a 13-step AI pipeline
4. **Validates** syntax, structure, and environment configuration
5. **Deploys** the server locally and hands you ready-to-paste client configs
6. **Pushes** to GitHub with one click (optional)

> **Think of it as "Vercel for MCP" — but the AI writes the entire server for you.**

---

## Demo

```
You:  "I need an MCP server that manages todo items with
       priorities and due dates"

MCP Factory:
  ✓ Designed architecture: 5 tools, 2 resources, 1 prompt
  ✓ Generated 13 files in Python
  ✓ Validated syntax and structure
  ✓ Deployed to localhost:3001/mcp
  ✓ Ready to connect from Claude Desktop, Cursor, or Windsurf
```

The entire flow — from description to running server — takes **under 60 seconds**.

---

## Key Features

| Feature | Description |
|---------|-------------|
| **Chat-to-Server** | Describe what you need in plain English. The AI asks smart clarifying questions and designs the full architecture. |
| **13-Step Pipeline** | Template copy → placeholder injection → LLM-powered tool/resource/prompt generation → validation → packaging → deployment. |
| **Dual Language** | Generates Python (FastMCP) or TypeScript (@modelcontextprotocol/sdk) servers — your choice. |
| **Auto-Deploy** | Generated servers are automatically installed, started, and made available on `localhost`. No manual setup. |
| **Client Configs** | Instant copy-paste configs for **Claude Desktop**, **Cursor**, **Windsurf**, and any MCP-compatible client. |
| **GitHub Push** | One-click repo creation and push. Enter a PAT, pick a name, and your code is on GitHub. |
| **Real-Time UI** | WebSocket-powered streaming. See the AI think, watch code generate step-by-step, track deployment progress live. |
| **Smart Prompts** | Heavily engineered LLM prompts enforce correct imports, shared store patterns, proper error handling, and SDK conventions. |
| **Multi-Provider** | Works with Groq, OpenAI, Ollama, Together AI, LM Studio, vLLM — any OpenAI-compatible API. |

---

## Quick Start

### Prerequisites

- **Python 3.11+** with [`uv`](https://docs.astral.sh/uv/) installed
- **Node.js 18+** with npm
- An LLM API key (Groq free tier works great)

### 1. Clone & Configure

```bash
git clone https://github.com/YOUR_USERNAME/mcp-factory.git
cd mcp-factory

# Set up environment
cp .env.example backend/.env
```

Edit `backend/.env` with your LLM provider credentials:

```env
LLM_PROVIDER=groq
LLM_MODEL=openai/gpt-oss-120b
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_API_KEY=your-groq-api-key
```

### 2. Start the Backend

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

### 3. Start the Frontend

```bash
cd frontend
npm install
npm run dev
```

### 4. Open & Build

Navigate to **http://localhost:5173** and describe the MCP server you want.

---

## How It Works

```
┌─────────────────────────────────────────────────────────────┐
│                        YOU (Browser)                         │
│   "I need an MCP server that manages GitHub issues and      │
│    sends Slack notifications"                                │
└─────────────────────┬───────────────────────────────────────┘
                      │ WebSocket
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                   INTELLIGENCE ENGINE                         │
│                                                               │
│  Phase 1: UNDERSTANDING                                       │
│    → Extract tools, APIs, features from description           │
│    → Identify gaps: auth method? language? scope?             │
│                                                               │
│  Phase 2: CLARIFYING                                          │
│    → Ask smart questions one at a time                        │
│    → User picks from option cards or types freely             │
│    → Merge answers, track completeness                        │
│                                                               │
│  Phase 3: DESIGNING                                           │
│    → Generate full MCPArchitecture JSON                       │
│    → Tools, resources, prompts, env vars, dependencies        │
│    → Show architecture card in UI                             │
└─────────────────────┬───────────────────────────────────────┘
                      │ User clicks "Generate Code"
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                  13-STEP CODE GENERATOR                       │
│                                                               │
│   1.  Copy language template (Python / TypeScript)            │
│   2.  Replace placeholders (name, description, version)       │
│   3.  Generate code blocks (imports, registrations, deps)     │
│   4.  LLM generates each tool file (with retry + postfix)    │
│   5.  LLM generates each resource file                       │
│   6.  LLM generates each prompt file                         │
│   7.  Rename package to match server name                    │
│   8.  Validate syntax, structure, env var consistency         │
│   9.  Regenerate .env.example with discovered vars            │
│  10.  Generate MCP client configs                             │
│  11.  Generate test stubs                                     │
│  12.  Generate README documentation                           │
│  13.  Package as ZIP                                          │
└─────────────────────┬───────────────────────────────────────┘
                      │ Automatic
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                    AUTO-DEPLOYER                               │
│                                                               │
│   1. Copy to ~/.mcp-factory/deployments/                      │
│   2. Install dependencies (uv sync / npm install)             │
│   3. Start server on dynamic port (3001-3099)                 │
│   4. Wait for TCP readiness                                   │
│   5. Generate client configs for Claude/Cursor/Windsurf       │
│   6. Server is LIVE at http://localhost:{port}/mcp            │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│               YOUR MCP SERVER IS RUNNING                      │
│                                                               │
│   → Copy config into Claude Desktop / Cursor / Windsurf      │
│   → Download source code as ZIP                               │
│   → Push to GitHub with one click                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Architecture

```
mcp-factory/
├── backend/                    # FastAPI + WebSocket server
│   ├── app/
│   │   ├── api/                # REST + WebSocket endpoints
│   │   ├── engine/             # Intelligence Engine (orchestrator, prompts)
│   │   ├── codegen/            # 13-step code generation pipeline
│   │   ├── models/             # Pydantic models (session, architecture, messages)
│   │   ├── services/           # LLM client, deployment manager, session manager
│   │   └── utils/              # JSON parser, helpers
│   └── pyproject.toml
│
├── frontend/                   # React + Vite + TypeScript
│   └── src/
│       ├── components/         # Chat, CodeGen, Options, Progress, Layout
│       ├── hooks/              # useChat, useWebSocket (useReducer state)
│       └── types/              # TypeScript message types
│
└── templates/                  # MCP server templates
    ├── python/                 # FastMCP template (Python 3.10+)
    ├── typescript/             # @modelcontextprotocol/sdk template (Node 18+)
    └── TEMPLATE_MANIFEST.json  # Template metadata & placeholder definitions
```

### Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | React 19, Vite 7, TypeScript 5.9, WebSocket |
| **Backend** | FastAPI, Uvicorn, Pydantic 2, WebSocket |
| **LLM** | Groq (default), OpenAI, Ollama, Together AI, LM Studio, vLLM |
| **Python MCP SDK** | FastMCP (mcp[cli] >= 1.2.0) |
| **TypeScript MCP SDK** | @modelcontextprotocol/sdk ^1.26.0 |
| **Package Manager** | uv (Python), npm (TypeScript/Frontend) |
| **State** | React useReducer (frontend), in-memory sessions (backend) |
| **Transport** | streamable-http (endpoint: `/mcp`) |

---

## Supported LLM Providers

MCP Factory works with any OpenAI-compatible API. Configure in `backend/.env`:

| Provider | `LLM_PROVIDER` | `LLM_BASE_URL` | Notes |
|----------|----------------|-----------------|-------|
| **Groq** | `groq` | `https://api.groq.com/openai/v1` | Free tier available. Fastest inference. |
| **OpenAI** | `openai` | `https://api.openai.com/v1` | GPT-4o recommended |
| **Ollama** | `ollama` | `http://localhost:11434` | Fully local. No API key needed. |
| **Together AI** | `together` | `https://api.together.xyz/v1` | Llama 3.3 70B works great |
| **LM Studio** | `lmstudio` | `http://localhost:1234/v1` | Local GUI. No API key needed. |
| **vLLM** | `vllm` | `http://localhost:8080/v1` | Self-hosted high-throughput |

---

## Client Configuration

After deployment, MCP Factory generates ready-to-use configs:

### Claude Desktop

```json
{
  "mcpServers": {
    "your-server": {
      "command": "npx",
      "args": ["@pyroprompts/mcp-stdio-to-streamable-http-adapter"],
      "env": { "URI": "http://localhost:3001/mcp" }
    }
  }
}
```

> Claude Desktop doesn't support HTTP directly — the adapter bridges stdio ↔ streamable-http.

### Cursor / Windsurf / Generic

```json
{
  "mcpServers": {
    "your-server": {
      "url": "http://localhost:3001/mcp"
    }
  }
}
```

---

## What Gets Generated

Every generated MCP server includes:

```
mcp-server-your-name/
├── pyproject.toml              # Dependencies, entry point, metadata
├── README.md                   # Auto-generated documentation
├── .env.example                # Environment variable template
├── .gitignore                  # Python/Node ignores
├── Dockerfile                  # Container-ready
├── src/
│   └── mcp_server_your_name/
│       ├── __init__.py         # Package entry + main()
│       ├── server.py           # FastMCP server setup
│       ├── tools/              # One file per tool (LLM-generated)
│       ├── resources/          # One file per resource (LLM-generated)
│       ├── prompts/            # One file per prompt (LLM-generated)
│       └── utils/
│           ├── store.py        # Shared in-memory store
│           └── validation.py   # Input validation helpers
└── tests/
    └── test_tools.py           # Generated test stubs
```

---

## Contributing

Contributions are welcome! Here are some areas that could use help:

- **More templates** — Add Go, Rust, or Java MCP server templates
- **Persistent storage** — Replace in-memory sessions with Redis/SQLite
- **Cloud deployment** — Deploy generated servers to Fly.io, Railway, or AWS
- **Template marketplace** — Share and discover community templates
- **Test generation** — Smarter LLM-powered test generation with actual assertions

---

## License

MIT

---

<div align="center">

**Built with AI, for AI.**

MCP Factory — because the best MCP server is the one you don't have to write.

</div>
