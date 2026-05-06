"""Scoped memory stores for research workflows."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any

from memory.conversation_memory import ConversationMemory, format_history_for_llm

if TYPE_CHECKING:
    from storage.report_cache import ReportCacheService
    from users.service import UserService


@dataclass
class MemorySnapshot:
    """Compacted memory snapshot passed to the coordinator."""

    session_context: dict[str, Any]
    conversation_summary: str
    user_preferences: dict[str, Any]
    instrument_memory: dict[str, Any]


class SessionMemoryStore:
    """Short-term chat memory backed by ConversationMemory."""

    def __init__(self, memory: ConversationMemory):
        self.memory = memory

    def snapshot(
        self,
        session_id: str | None,
        history: list[dict] | None = None,
        max_messages: int = 6,
    ) -> tuple[dict[str, Any], str]:
        if not session_id:
            return {}, format_history_for_llm(history or [], max_history_messages=max_messages)

        session_context = self.memory.get_context(session_id)
        session_history = history if history is not None else self.memory.get_history(session_id)
        return session_context, compact_conversation_history(session_history, max_messages=max_messages)


class UserPreferenceMemoryStore:
    """Persistent user preference memory backed by the users module."""

    def __init__(self, user_service: "UserService | None" = None):
        self.user_service = user_service

    def get_preferences(self, user_id: str | None) -> dict[str, Any]:
        if not user_id or not self.user_service:
            return {}
        try:
            user = self.user_service.get_user(user_id)
        except Exception:
            return {}
        if not user:
            return {}
        return {
            "preferred_markets": getattr(user.preferences, "preferred_markets", []),
            "watched_stocks": getattr(user.preferences, "watched_stocks", []),
            "watched_industries": getattr(user.preferences, "watched_industries", []),
            "notification_time": getattr(user.preferences, "notification_time", None),
            "email_enabled": getattr(user.preferences, "email_enabled", None),
        }


class InstrumentMemoryStore:
    """Instrument/company memory derived from report cache metadata."""

    def __init__(self, report_cache: "ReportCacheService | None" = None):
        self.report_cache = report_cache

    def get_memory(self, symbol: str | None, query: str | None = None) -> dict[str, Any]:
        if not self.report_cache or not symbol:
            return {}
        try:
            cached = self.report_cache.find_cached_report(query or symbol, symbol=symbol)
        except TypeError:
            cached = self.report_cache.find_cached_report(query or symbol)
        except Exception:
            return {}
        if not cached:
            return {}
        return {
            "symbol": symbol,
            "last_recommendation": cached.recommendation,
            "last_target_price": cached.target_price,
            "last_generated_at": cached.generated_at.isoformat() if cached.generated_at else None,
            "sources": cached.data_sources,
        }


class ResearchMemoryLayer:
    """Combine scoped memory stores into a compact coordinator snapshot."""

    def __init__(
        self,
        session_store: SessionMemoryStore,
        user_store: UserPreferenceMemoryStore | None = None,
        instrument_store: InstrumentMemoryStore | None = None,
    ):
        self.session_store = session_store
        self.user_store = user_store or UserPreferenceMemoryStore()
        self.instrument_store = instrument_store or InstrumentMemoryStore()

    def snapshot(
        self,
        session_id: str | None,
        history: list[dict] | None,
        user_id: str | None,
        symbol: str | None,
        query: str,
    ) -> MemorySnapshot:
        session_context, conversation_summary = self.session_store.snapshot(session_id, history)
        return MemorySnapshot(
            session_context=session_context,
            conversation_summary=conversation_summary,
            user_preferences=self.user_store.get_preferences(user_id),
            instrument_memory=self.instrument_store.get_memory(symbol, query),
        )


def compact_conversation_history(history: list[dict], max_messages: int = 6, max_chars: int = 3000) -> str:
    """Bound conversation history before it enters LLM prompts."""
    formatted = format_history_for_llm(history or [], max_history_messages=max_messages)
    if len(formatted) <= max_chars:
        return formatted

    omitted = len(formatted) - max_chars
    return (
        "[对话历史压缩]\n"
        f"已省略约 {omitted} 个字符，仅保留最近上下文。\n\n"
        f"{formatted[-max_chars:]}\n\n"
        f"[压缩时间: {datetime.now().isoformat()}]"
    )
