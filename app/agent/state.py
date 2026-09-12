from __future__ import annotations

from typing import TypedDict


class AgentState(TypedDict, total=False):
    """Data passed between the inspect, plan, execute, and finalize nodes."""

    chat_id: str
    request: str
    file_path: str | None
    file_name: str | None
    metadata: dict | None
    plan: dict | None
    result: dict | None
    stats: dict | None
    chart_type: str | None
    chart_web: str | None
    explanation: str | None
    insights: list | None
    warnings: list | None
    error: str | None
    needs_input: bool
    bot_message: dict | None