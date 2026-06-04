"""
memory/conversation_history.py
────────────────────────────────
Per-session voice conversation history.
"""

import structlog
from datetime import datetime, timezone

logger = structlog.get_logger(__name__)


class ConversationHistory:

    def __init__(self):
        self._sessions: dict[str, list] = {}

    def start_session(self, session_id: str) -> None:
        """Start a new voice session."""
        self._sessions[session_id] = []
        logger.info("conversation.session_started", session_id=session_id)

    def add_turn(
        self,
        session_id: str,
        role: str,
        content: str,
    ) -> None:
        """Add a turn to the conversation history."""
        if session_id not in self._sessions:
            self.start_session(session_id)
        self._sessions[session_id].append({
            "role":      role,
            "content":   content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def get_history(self, session_id: str) -> list:
        """Get full conversation history for a session."""
        return self._sessions.get(session_id, [])

    def get_last_n(self, session_id: str, n: int = 5) -> list:
        """Get last N turns of a session."""
        history = self._sessions.get(session_id, [])
        return history[-n:]

    def end_session(self, session_id: str) -> list:
        """End a session and return its history."""
        history = self._sessions.pop(session_id, [])
        logger.info("conversation.session_ended", session_id=session_id, turns=len(history))
        return history

    def clear_all(self) -> None:
        """Clear all session history."""
        self._sessions.clear()
