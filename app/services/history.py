from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

from ..config import CHAT_DB_FILE, HISTORY_PAGE_SIZE

_lock = threading.RLock()


def _now() -> str:
    """Return one consistent UTC timestamp format for persisted records."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _read() -> dict:
    """Read the JSON database, treating missing/corrupt history as empty."""
    if not CHAT_DB_FILE.exists():
        return {"chats": []}
    try:
        return json.loads(CHAT_DB_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"chats": []}


def _write(data: dict) -> None:
    """Atomically replace the history file to avoid partially written JSON."""
    tmp = CHAT_DB_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(CHAT_DB_FILE)


def list_chats(limit: int = HISTORY_PAGE_SIZE) -> list[dict]:
    """Return the newest chats first, limited for a responsive history panel."""
    with _lock:
        data = _read()
    chats = sorted(data.get("chats", []), key=lambda c: c.get("updated_at", ""), reverse=True)
    return chats[:limit]


def get_chat(chat_id: str) -> dict | None:
    """Find one chat by ID while holding the persistence lock."""
    with _lock:
        for chat in _read().get("chats", []):
            if chat.get("id") == chat_id:
                return chat
    return None


def delete_chat(chat_id: str) -> bool:
    """Remove a chat and its messages; return whether an item was removed."""
    with _lock:
        data = _read()
        chats = data.get("chats", [])
        remaining = [chat for chat in chats if chat.get("id") != chat_id]
        if len(remaining) == len(chats):
            return False
        data["chats"] = remaining
        _write(data)
    return True


def create_chat(title: str = "New Chat") -> dict:
    """Create and persist a chat with an empty message list."""
    chat = {
        "id": str(uuid.uuid4()),
        "title": title,
        "created_at": _now(),
        "updated_at": _now(),
        "messages": [],
    }
    with _lock:
        data = _read()
        data["chats"].append(chat)
        _write(data)
    return chat


def touch_chat(chat_id: str, title: str | None = None) -> None:
    """Update activity time and assign the first user-facing title when provided."""
    with _lock:
        data = _read()
        for chat in data.get("chats", []):
            if chat.get("id") == chat_id:
                chat["updated_at"] = _now()
                if title and chat.get("title") == "New Chat":
                    chat["title"] = title[:60]
                break
        else:
            return
        _write(data)


def append_message(chat_id: str, message: dict) -> dict:
    """Timestamp and append one message, creating a missing chat defensively."""
    # Copy input so persistence adds its timestamp without mutating route state.
    message = dict(message)
    message["ts"] = _now()
    with _lock:
        data = _read()
        target = next(
            (chat for chat in data.get("chats", []) if chat.get("id") == chat_id),
            None,
        )
        if target is None:
            target = {"id": chat_id, "title": "New Chat", "messages": []}
            data["chats"].append(target)
        target["messages"].append(message)
        target["updated_at"] = _now()
        _write(data)
    return message