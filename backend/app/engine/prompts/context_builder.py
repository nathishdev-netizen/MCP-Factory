from __future__ import annotations

from app.models.session import Session, ConversationPhase
from app.models.messages import TextContent
from app.services.template_loader import template_loader
from app.engine.prompts.system_base import SYSTEM_BASE_PROMPT
from app.engine.prompts.understanding import UNDERSTANDING_PROMPT
from app.engine.prompts.clarification import build_clarification_prompt
from app.engine.prompts.architecture import build_architecture_prompt


def build_prompt(session: Session) -> list[dict]:
    """Build the complete prompt messages array for Ollama.

    Layers:
    1. System base (identity + MCP knowledge)
    2. Template constraints (from TEMPLATE_MANIFEST.json)
    3. Phase-specific instructions (understanding / clarification / architecture)
    4. Conversation history
    """
    # Layer 1 + 2: System base + template constraints
    system_content = SYSTEM_BASE_PROMPT

    if template_loader.is_loaded:
        system_content += "\n\n" + template_loader.get_constraints_text()

    # Layer 3: Phase-specific prompt
    if session.phase in (ConversationPhase.INITIAL, ConversationPhase.UNDERSTANDING):
        system_content += "\n\n" + UNDERSTANDING_PROMPT

    elif session.phase == ConversationPhase.CLARIFYING:
        req_json = session.requirements.model_dump_json(indent=2)
        system_content += "\n\n" + build_clarification_prompt(req_json)

    elif session.phase == ConversationPhase.DESIGNING:
        req_json = session.requirements.model_dump_json(indent=2)
        system_content += "\n\n" + build_architecture_prompt(req_json)

    messages = [{"role": "system", "content": system_content}]

    # Layer 4: Conversation history
    for msg in session.messages:
        role = msg.role.value
        # Extract text from content blocks
        text_parts = []
        for block in msg.content:
            if isinstance(block, TextContent):
                text_parts.append(block.text)
        if text_parts:
            messages.append({"role": role, "content": "\n".join(text_parts)})

    return messages
