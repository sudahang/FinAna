"""Conversation memory management for multi-turn chat support."""

import uuid
import time
from typing import TypedDict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import OrderedDict


@dataclass
class Message:
    """A single message in the conversation."""
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: float = field(default_factory=time.time)
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert message to dictionary."""
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Message":
        """Create message from dictionary."""
        return cls(
            role=data.get("role", "user"),
            content=data.get("content", ""),
            timestamp=data.get("timestamp", time.time()),
            metadata=data.get("metadata", {})
        )


@dataclass
class ConversationSession:
    """A conversation session with history and metadata."""
    session_id: str
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    messages: list[Message] = field(default_factory=list)
    context: dict = field(default_factory=dict)  # Store extracted params, analysis results, etc.

    def add_message(self, role: str, content: str, metadata: dict = None) -> Message:
        """Add a message to the conversation."""
        msg = Message(
            role=role,
            content=content,
            metadata=metadata or {}
        )
        self.messages.append(msg)
        self.last_accessed = time.time()
        return msg

    def get_history(self, max_messages: int = None) -> list[dict]:
        """Get conversation history as list of dicts."""
        messages = self.messages
        if max_messages:
            messages = messages[-max_messages:]
        return [msg.to_dict() for msg in messages]

    def clear(self):
        """Clear conversation history."""
        self.messages = []
        self.context = {}
        self.last_accessed = time.time()

    def to_dict(self) -> dict:
        """Convert session to dictionary."""
        return {
            "session_id": self.session_id,
            "created_at": self.created_at,
            "last_accessed": self.last_accessed,
            "messages": [msg.to_dict() for msg in self.messages],
            "context": self.context
        }


class ConversationMemory:
    """
    Manages conversation sessions and history for multi-turn chat.

    Features:
    - Session-based memory with unique session IDs
    - Automatic session cleanup based on TTL
    - Context storage for sharing data across turns
    - Thread-safe operations
    """

    def __init__(
        self,
        max_sessions: int = 1000,
        session_ttl: int = 3600,  # 1 hour in seconds
        max_messages_per_session: int = 50
    ):
        """
        Initialize conversation memory.

        Args:
            max_sessions: Maximum number of sessions to keep in memory
            session_ttl: Session time-to-live in seconds
            max_messages_per_session: Maximum messages to keep per session
        """
        self._sessions: OrderedDict[str, ConversationSession] = OrderedDict()
        self.max_sessions = max_sessions
        self.session_ttl = session_ttl
        self.max_messages_per_session = max_messages_per_session

    def create_session(self, session_id: str = None) -> str:
        """
        Create a new conversation session.

        Args:
            session_id: Optional session ID. If None, generates a new one.

        Returns:
            The session ID.
        """
        if session_id is None:
            session_id = str(uuid.uuid4())

        # Check if we need to evict old sessions
        if len(self._sessions) >= self.max_sessions:
            self._evict_oldest()

        session = ConversationSession(session_id=session_id)
        self._sessions[session_id] = session
        return session_id

    def get_session(self, session_id: str) -> ConversationSession | None:
        """
        Get a conversation session by ID.

        Args:
            session_id: The session ID to retrieve.

        Returns:
            The session if found, None otherwise.
        """
        session = self._sessions.get(session_id)
        if session:
            # Update last accessed time
            session.last_accessed = time.time()
            # Move to end (most recently used)
            self._sessions.move_to_end(session_id)
        return session

    def get_or_create_session(self, session_id: str = None) -> ConversationSession:
        """
        Get existing session or create new one.

        Args:
            session_id: Optional session ID. If None or not found, creates new.

        Returns:
            The conversation session.
        """
        if session_id:
            session = self.get_session(session_id)
            if session:
                return session

        # Create new session
        session_id = self.create_session(session_id)
        return self._sessions[session_id]

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: dict = None
    ) -> Message:
        """
        Add a message to a conversation session.

        Args:
            session_id: The session ID.
            role: Message role ('user' or 'assistant').
            content: Message content.
            metadata: Optional metadata.

        Returns:
            The created message, or None if session not found.
        """
        session = self.get_session(session_id)
        if not session:
            session = self.get_or_create_session(session_id)

        # Enforce max messages limit
        if len(session.messages) >= self.max_messages_per_session:
            # Remove oldest message
            session.messages.pop(0)

        return session.add_message(role, content, metadata)

    def get_history(
        self,
        session_id: str,
        max_messages: int = None
    ) -> list[dict]:
        """
        Get conversation history for a session.

        Args:
            session_id: The session ID.
            max_messages: Maximum number of messages to return.

        Returns:
            List of message dictionaries, or empty list if session not found.
        """
        session = self.get_session(session_id)
        if not session:
            return []

        return session.get_history(max_messages)

    def get_context(self, session_id: str, key: str = None) -> dict:
        """
        Get context data from a session.

        Args:
            session_id: The session ID.
            key: Optional key to get specific context value.

        Returns:
            Context dictionary or specific value.
        """
        session = self.get_session(session_id)
        if not session:
            return {}

        if key:
            return session.context.get(key)
        return session.context

    def set_context(self, session_id: str, key: str, value) -> bool:
        """
        Set context data in a session.

        Args:
            session_id: The session ID.
            key: Context key.
            value: Context value.

        Returns:
            True if successful, False if session not found.
        """
        session = self.get_session(session_id)
        if not session:
            return False

        session.context[key] = value
        return True

    def update_context(self, session_id: str, updates: dict) -> bool:
        """
        Update multiple context values in a session.

        Args:
            session_id: The session ID.
            updates: Dictionary of key-value pairs to update.

        Returns:
            True if successful, False if session not found.
        """
        session = self.get_session(session_id)
        if not session:
            return False

        session.context.update(updates)
        return True

    def clear_session(self, session_id: str) -> bool:
        """
        Clear a conversation session's history.

        Args:
            session_id: The session ID.

        Returns:
            True if successful, False if session not found.
        """
        session = self.get_session(session_id)
        if not session:
            return False

        session.clear()
        return True

    def delete_session(self, session_id: str) -> bool:
        """
        Delete a conversation session.

        Args:
            session_id: The session ID.

        Returns:
            True if deleted, False if session not found.
        """
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    def cleanup_expired_sessions(self) -> int:
        """
        Remove expired sessions based on TTL.

        Returns:
            Number of sessions removed.
        """
        current_time = time.time()
        expired = [
            sid for sid, session in self._sessions.items()
            if current_time - session.last_accessed > self.session_ttl
        ]

        for sid in expired:
            del self._sessions[sid]

        return len(expired)

    def _evict_oldest(self):
        """Evict the oldest session (LRU)."""
        if self._sessions:
            # Pop the first item (oldest)
            self._sessions.popitem(last=False)

    def get_session_info(self, session_id: str) -> dict | None:
        """
        Get session metadata without messages.

        Args:
            session_id: The session ID.

        Returns:
            Session info dict or None if not found.
        """
        session = self.get_session(session_id)
        if not session:
            return None

        return {
            "session_id": session.session_id,
            "created_at": session.created_at,
            "last_accessed": session.last_accessed,
            "message_count": len(session.messages),
            "context_keys": list(session.context.keys())
        }

    def list_sessions(self) -> list[dict]:
        """
        List all active sessions.

        Returns:
            List of session info dictionaries.
        """
        # Cleanup expired first
        self.cleanup_expired_sessions()

        return [
            self.get_session_info(sid)
            for sid in self._sessions
        ]

    def get_stats(self) -> dict:
        """
        Get memory statistics.

        Returns:
            Dictionary with memory stats.
        """
        return {
            "total_sessions": len(self._sessions),
            "max_sessions": self.max_sessions,
            "session_ttl": self.session_ttl,
            "max_messages_per_session": self.max_messages_per_session
        }


# Global singleton instance
_conversation_memory: ConversationMemory | None = None


def get_conversation_memory() -> ConversationMemory:
    """Get singleton instance of ConversationMemory."""
    global _conversation_memory
    if _conversation_memory is None:
        _conversation_memory = ConversationMemory(
            max_sessions=1000,
            session_ttl=3600,  # 1 hour
            max_messages_per_session=50
        )
    return _conversation_memory


def format_history_for_llm(
    history: list[dict],
    include_system_prompt: bool = True,
    max_history_messages: int = 10
) -> str:
    """
    Format conversation history for LLM context.

    Args:
        history: List of message dictionaries.
        include_system_prompt: Whether to include system-style context.
        max_history_messages: Maximum messages to include.

    Returns:
        Formatted history string.
    """
    if not history:
        return ""

    # Limit to recent messages
    recent_history = history[-max_history_messages:]

    formatted = []
    if include_system_prompt:
        formatted.append("[对话历史开始]")

    for msg in recent_history:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        role_label = "用户" if role == "user" else "助手"
        formatted.append(f"{role_label}: {content}")

    if include_system_prompt:
        formatted.append("[对话历史结束]")

    return "\n\n".join(formatted)
