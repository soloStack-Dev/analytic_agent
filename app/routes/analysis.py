from __future__ import annotations

from ..agent.graph import agent


def analyze_chat(
    chat_id: str,
    request: str,
    file_path: str | None,
    file_name: str | None,
) -> dict:
    """Invoke the graph and return its presentation-ready bot message."""
    # Keep route code independent from graph internals by passing one explicit state.
    result = agent.invoke(
        {
            "chat_id": chat_id,
            "request": request,
            "file_path": file_path,
            "file_name": file_name,
        }
    )
    bot_message = result.get("bot_message")
    if bot_message is None:
        # A defensive fallback protects the chat UI if a graph node returns no message.
        bot_message = {
            "role": "assistant",
            "kind": "error",
            "text": "The agent produced no response. Please try again.",
            "insights": [],
            "warnings": [],
            "chart": None,
            "chart_type": None,
            "plan": None,
            "meta": None,
        }
    return bot_message