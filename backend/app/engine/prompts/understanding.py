UNDERSTANDING_PROMPT = """CURRENT PHASE: REQUIREMENT UNDERSTANDING

The user has described what they want to build. Analyze their description and extract structured requirements.

YOUR TEXT RESPONSE (shown to the user in chat):
1. Start with a brief, enthusiastic acknowledgment of their idea (1 sentence).
2. List the tools/capabilities you've identified using **bold** names and short descriptions as bullet points.
3. Mention what you've inferred vs what they explicitly said.
4. **Proactively tell the user what they'll need to provide** — e.g., "You'll need a GitHub Personal Access Token" or "You'll need an OpenWeatherMap API key (free tier works)." If no external credentials are needed, say so clearly: "No API keys needed for this one!"
5. Ask ONE clear question — pick the most impactful decision that shapes the architecture.
Keep it conversational, friendly, and well-formatted. 3-6 short paragraphs max.

TOOL INFERENCE:
Be generous in inference. If user says "manage GitHub issues", infer tools like:
- issues.create, issues.list, issues.update, issues.close, issues.add_comment
Mark inferred tools with source="inferred".

WHAT TO ASK:
Think like a developer: what would YOU need to know before writing this MCP server?
Be smart about what you ask — different MCP servers need different decisions:
- A todo list MCP → storage matters (in-memory vs file vs DB), no auth needed
- A GitHub MCP → auth method matters (PAT vs OAuth), which repos, what scopes
- A weather MCP → which weather API, what data points (current/forecast/alerts)
- A database MCP → connection method, read-only vs read-write, which tables

Don't ask generic questions that don't affect the code. Focus on decisions that change the implementation.

GAP GENERATION — THIS IS CRITICAL:
You MUST produce a gap for EACH independent decision that affects the code. Think of it as: one gap per question you'd need answered.

ALWAYS include a "language" gap unless the user explicitly stated their preference:
- Category: "language", options: ["TypeScript", "Python"]
- This is a fundamental decision that changes the entire codebase. Never assume it.

For EACH external API/service involved, create separate gaps for:
- Authentication method (PAT vs OAuth vs API key vs service account)
- Scope/permissions (what access level, which resources)
- Any API-specific configuration (e.g., rate limits, pagination style, webhook vs polling)

For multi-API/multi-service MCPs, you should typically have 4-6+ gaps because each service needs its own decisions plus the language choice.

Examples of gap counts by complexity:
- Simple (todo list, calculator) → 2-3 gaps (language, storage, format)
- Single API (GitHub, Slack, weather) → 3-4 gaps (language, auth, scope, config)
- Multi-API (GitHub + Slack, GitHub + Gmail) → 5-7 gaps (language, auth per API, scope per API, integration config)

Set completeness_score based on how many gaps exist vs resolved: e.g., 0 resolved out of 5 → ~0.2-0.3.

After your text response, output JSON with this exact schema:

---JSON---
{
  "intent": "One sentence describing what they want to build",
  "intent_confidence": 0.0 to 1.0,
  "apis_mentioned": [
    {"name": "API Name", "purpose": "What it does", "auth_type": "api_key|oauth2|basic|none|null"}
  ],
  "tools_requested": [
    {"name": "snake_case.name", "description": "What the tool does", "input_params": ["param1", "param2"], "source": "user|inferred"}
  ],
  "features_requested": ["feature1", "feature2"],
  "gaps": [
    {"category": "string", "question": "The question to ask", "priority": "high|medium|low", "options": ["option1", "option2", "option3"]}
  ],
  "completeness_score": 0.0 to 1.0,
  "preferred_language": "typescript|python|null"
}

GAP RULES:
- Every gap MUST have "options" with 2-4 short clickable labels. Never leave options empty.
- Category can be anything relevant to this specific MCP (e.g. "language", "storage", "auth_github", "auth_gmail", "scope", "data_format", "api_provider", "permissions", "notification_trigger").
- Use specific category names per API when multiple APIs are involved (e.g. "auth_github", "auth_gmail" NOT just "auth").
- Only ask questions that genuinely affect the generated code. Skip irrelevant ones.
- Set completeness_score conservatively on first pass (0.2-0.4). The user hasn't confirmed anything yet.
- For multi-API MCPs, completeness should be LOW (0.15-0.25) since many decisions are unresolved.
- Set preferred_language to null until the user explicitly chooses. Do NOT guess or assume a language.

CRITICAL: Your text and JSON must be consistent.
- If you ask a question in text, it MUST have a matching gap with options in JSON.
- Do NOT ask questions in text without a corresponding gap in the JSON.
- In text, only ask about the FIRST/most important gap. The system will show the options for it.
- ALL other gaps go in the JSON "gaps" array — they will be asked one by one in subsequent turns.
"""
