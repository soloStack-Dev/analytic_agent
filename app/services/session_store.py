from __future__ import annotations

import threading


class SessionStore:
    """Thread-safe in-memory cache for chat DataFrames and metadata."""

    def __init__(self) -> None:
        self._data: dict[str, dict] = {}
        self._lock = threading.Lock()

    def get(self, chat_id: str, key: str, default=None):
        """Read one cached value without exposing the internal dictionary."""
        with self._lock:
            return self._data.get(chat_id, {}).get(key, default)

    def set(self, chat_id: str, key: str, value) -> None:
        """Store one DataFrame or metadata value under a chat-scoped key."""
        with self._lock:
            self._data.setdefault(chat_id, {})[key] = value

    def pop(self, chat_id: str) -> None:
        """Remove all cached values when a chat session is discarded."""
        with self._lock:
            self._data.pop(chat_id, None)


store = SessionStore()