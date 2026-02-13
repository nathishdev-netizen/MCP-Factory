from __future__ import annotations

from datetime import datetime, timezone

from app.models.session import Session, ConversationPhase
from app.models.messages import ChatMessage
from app.models.requirements import ExtractedRequirements
from app.models.architecture import MCPArchitecture


class SessionManager:
    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}

    def create_session(self) -> Session:
        session = Session()
        self._sessions[session.id] = session
        return session

    def get_session(self, session_id: str) -> Session | None:
        return self._sessions.get(session_id)

    def add_message(self, session_id: str, message: ChatMessage) -> None:
        session = self._sessions[session_id]
        session.messages.append(message)
        session.updated_at = datetime.now(timezone.utc)

    def update_requirements(self, session_id: str, requirements: ExtractedRequirements) -> None:
        session = self._sessions[session_id]
        session.requirements = requirements
        session.updated_at = datetime.now(timezone.utc)

    def set_phase(self, session_id: str, phase: ConversationPhase) -> None:
        session = self._sessions[session_id]
        session.phase = phase
        session.updated_at = datetime.now(timezone.utc)

    def set_architecture(self, session_id: str, architecture: MCPArchitecture) -> None:
        session = self._sessions[session_id]
        session.architecture = architecture
        session.phase = ConversationPhase.COMPLETE
        session.updated_at = datetime.now(timezone.utc)

    def increment_clarification(self, session_id: str) -> int:
        session = self._sessions[session_id]
        session.clarification_rounds += 1
        return session.clarification_rounds

    def set_zip_path(self, session_id: str, zip_path: str) -> None:
        session = self._sessions[session_id]
        session.zip_path = zip_path
        session.updated_at = datetime.now(timezone.utc)

    def set_generation_started(self, session_id: str) -> None:
        session = self._sessions[session_id]
        session.generation_started = True
        session.updated_at = datetime.now(timezone.utc)

    def list_sessions(self) -> list[Session]:
        return list(self._sessions.values())

    def count(self) -> int:
        return len(self._sessions)

    def clear(self) -> None:
        self._sessions.clear()


session_manager = SessionManager()
