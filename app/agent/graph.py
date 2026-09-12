from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from .nodes import execute_node, finalize_node, inspect_node, plan_node
from .state import AgentState


def _after_inspect(state: AgentState) -> str:
    """Stop on file/session errors; otherwise continue to plan selection."""
    return "finalize" if state.get("error") else "plan"


def _after_plan(state: AgentState) -> str:
    """Stop on an invalid plan; otherwise execute the validated plan."""
    return "finalize" if state.get("error") else "execute"


def build_agent():
    """Build the fixed analysis pipeline used for every chat request."""
    builder = StateGraph(AgentState)
    builder.add_node("inspect", inspect_node)
    builder.add_node("plan", plan_node)
    builder.add_node("execute", execute_node)
    builder.add_node("finalize", finalize_node)

    # Each stage returns partial state; conditional edges route errors directly
    # to the response builder so users receive a useful message instead of a 500.
    builder.add_edge(START, "inspect")
    builder.add_conditional_edges(
        "inspect",
        _after_inspect,
        {"finalize": "finalize", "plan": "plan"},
    )
    builder.add_conditional_edges(
        "plan",
        _after_plan,
        {"finalize": "finalize", "execute": "execute"},
    )
    builder.add_edge("execute", "finalize")
    builder.add_edge("finalize", END)
    return builder.compile()


agent = build_agent()