from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


# -- Content types -------------------------------------------------------

class TextContent(BaseModel):
    type: str = "text"
    text: str


class OptionItem(BaseModel):
    id: str
    label: str
    description: str | None = None


class OptionsContent(BaseModel):
    type: str = "options"
    question: str
    question_id: str
    options: list[OptionItem]
    allow_multiple: bool = False
    allow_freeform: bool = True


class ProgressContent(BaseModel):
    type: str = "progress"
    phase: str
    message: str


class ArchitectureContent(BaseModel):
    type: str = "architecture"
    summary: dict[str, Any]


ContentType = TextContent | OptionsContent | ProgressContent | ArchitectureContent


# -- Chat message ---------------------------------------------------------

class ChatMessage(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    role: MessageRole
    content: list[ContentType]
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# -- WebSocket protocol ---------------------------------------------------

class WSMessageType(str, Enum):
    # Client -> Server
    USER_MESSAGE = "user_message"
    OPTION_SELECTED = "option_selected"
    GENERATE_CODE = "generate_code"

    # Server -> Client
    ASSISTANT_CHUNK = "assistant_chunk"
    ASSISTANT_COMPLETE = "assistant_complete"
    SYSTEM_MESSAGE = "system_message"
    OPTIONS_PROMPT = "options_prompt"
    ARCHITECTURE_READY = "architecture_ready"
    GENERATION_PROGRESS = "generation_progress"
    GENERATION_COMPLETE = "generation_complete"
    DEPLOYMENT_PROGRESS = "deployment_progress"
    DEPLOYMENT_COMPLETE = "deployment_complete"
    ERROR = "error"


class WSFrame(BaseModel):
    type: WSMessageType
    session_id: str
    payload: dict[str, Any]
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
