from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field

from app.models.messages import ChatMessage
from app.models.requirements import ExtractedRequirements
from app.models.architecture import MCPArchitecture


class ConversationPhase(str, Enum):
    INITIAL = "initial"
    UNDERSTANDING = "understanding"
    CLARIFYING = "clarifying"
    DESIGNING = "designing"
    COMPLETE = "complete"
    GENERATING = "generating"


class Session(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    phase: ConversationPhase = ConversationPhase.INITIAL
    messages: list[ChatMessage] = Field(default_factory=list)
    requirements: ExtractedRequirements = Field(default_factory=ExtractedRequirements)
    architecture: MCPArchitecture | None = None
    clarification_rounds: int = 0
    zip_path: str | None = None
    generation_started: bool = False
    user_env_vars: dict[str, str] = Field(default_factory=dict)
