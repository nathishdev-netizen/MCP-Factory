CLARIFICATION_PROMPT_TEMPLATE = """CURRENT PHASE: REQUIREMENT CLARIFICATION

The user has answered a clarifying question. Update the requirements based on their answer.

CURRENT REQUIREMENTS STATE:
{current_requirements}

The user's response is the latest message in the conversation history.

YOUR TEXT RESPONSE (shown to the user in chat):
1. Briefly acknowledge their answer (e.g., "Great, in-memory storage it is!").
2. Summarize what you now know — use a short bullet list of confirmed decisions so far.
3. **Proactively inform the user about what they'll need**: API keys, accounts, credentials, access tokens, or anything they need to set up before using the MCP server. For example: "Heads up — you'll need to create a GitHub Personal Access Token with `repo` scope." If nothing is needed, say: "No external credentials needed for this setup!"
4. If there's still a decision that affects the code, ask ONE follow-up question. Explain briefly why it matters.
5. If all essential decisions are made, tell the user you have what you need and will now design.
Keep it friendly, concise, and well-formatted. 2-4 short paragraphs max.

LOGIC:
1. Merge ONLY the user's specific answer into the existing requirements. Resolve ONLY the gap that was directly answered.
2. Do NOT resolve or infer answers to OTHER unasked gaps based on the user's answer to one gap.
   - Example: If user chose "Personal Access Token" for GitHub auth, do NOT auto-resolve Gmail auth. Gmail needs its own confirmation.
   - Example: If user chose "in-memory" for storage, do NOT auto-resolve data format. Ask separately.
3. Carry forward ALL previously unresolved gaps that the user has NOT directly answered yet.
4. Think about what's STILL genuinely unknown for generating working code for THIS specific MCP:
   - For EACH external API: Is its auth method confirmed by the user? (Not inferred!)
   - For EACH external API: Are its scopes/permissions confirmed?
   - Are there implementation choices that change the code (storage, scope, format, permissions)?
5. If a decision that materially affects code is still missing, add it as a gap with options.
6. Don't ask about things that don't change the implementation.
7. Recalculate completeness_score: increase by ~0.10-0.15 per answered question. Be conservative.
8. Set ready_to_design=true ONLY when ALL of the following are true:
   - Every external API's auth method has been EXPLICITLY confirmed by the user
   - All high/medium priority gaps have been answered (not inferred)
   - You genuinely can't think of any remaining decision that would change the generated code

After your text response, output JSON:

---JSON---
{{
  "intent": "Updated intent if clarified",
  "intent_confidence": 0.0 to 1.0,
  "apis_mentioned": [...updated list...],
  "tools_requested": [...updated list...],
  "features_requested": [...updated list...],
  "gaps": [...only UNRESOLVED gaps that user has NOT directly answered...],
  "completeness_score": 0.0 to 1.0,
  "preferred_language": "typescript|python|null",
  "auth_requirements": [...as strings...],
  "env_vars_known": [...as strings...],
  "ready_to_design": true or false
}}

CRITICAL RULES — your text and JSON MUST be consistent:
- If ready_to_design is TRUE: your text must NOT ask any questions. Say "I have everything I need."
- If ready_to_design is FALSE: your "gaps" array MUST contain at least one entry with options.
- Every gap MUST have "options": ["opt1", "opt2", ...] with 2-4 clickable choices.
- auth_requirements and env_vars_known must be lists of strings, not objects.
- Ask ONE question at a time in your text. Match it to the FIRST gap in the JSON.
- Do NOT ask a question in text without a corresponding gap in JSON.
- Do NOT resolve gaps the user hasn't been asked about yet. Keep them in the gaps array.
"""


def build_clarification_prompt(current_requirements_json: str) -> str:
    return CLARIFICATION_PROMPT_TEMPLATE.format(
        current_requirements=current_requirements_json,
    )
