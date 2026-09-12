from __future__ import annotations

from pathlib import Path

from ..analysis import analyzer
from ..analysis.statistics import build_metadata
from ..charts import generator as chart_gen
from ..logger import logger
from ..services.file_reader import FileReadError, load_dataframe
from ..services.llm import LLMError, call_llm_json, is_configured
from ..services.session_store import store
from .state import AgentState
from . import tools


def inspect_node(state: AgentState) -> dict:
    """Load the dataset once and expose metadata to the planning stage."""
    chat_id = state.get("chat_id")
    file_path = state.get("file_path")

    # Follow-up questions reuse the DataFrame cached for this chat session.
    df = store.get(chat_id, "df")
    if file_path:
        # A newly attached file replaces the session dataset for subsequent turns.
        try:
            df = load_dataframe(Path(file_path))
            store.set(chat_id, "df", df)
        except FileReadError as exc:
            logger.error("file load failed for %s: %s", file_path, exc)
            return {
                "error": f"Could not read the uploaded file: {exc}",
            }

    if df is None:
        # The graph treats this as a user-facing state rather than an exception.
        return {
            "needs_input": True,
            "error": (
                "Please upload a dataset file (CSV, JSON, XLSX, or XLS) "
                "so I can analyze it."
            ),
        }

    file_name = state.get("file_name")
    if not file_name and file_path:
        file_name = Path(file_path).name
    # Only metadata crosses into the planner; raw rows stay in the session store.
    meta = build_metadata(df, file_name or "uploaded file")
    store.set(chat_id, "meta", meta)
    return {"metadata": meta}


def plan_node(state: AgentState) -> dict:
    """Choose an LLM plan when configured, otherwise use the offline planner."""
    metadata = state.get("metadata") or {}
    request = state.get("request", "")

    raw: dict | None = None
    if is_configured():
        # The model proposes structure only; validate_plan constrains every choice.
        try:
            system, user = tools.build_plan_prompt(metadata, request)
            raw = call_llm_json(system, user)
        except LLMError as exc:
            logger.error("LLM planning failed, using heuristic fallback: %s", exc)

    if not isinstance(raw, dict):
        # Offline mode keeps the product usable without an API key or network.
        plan = tools.heuristic_plan(metadata, request)
        warnings: list[str] = []
    else:
        plan, warnings = tools.validate_plan(raw, metadata)

    return {"plan": plan, "warnings": warnings}


def _explain(metadata: dict, plan: dict, stats: dict, request: str):
    """Create a grounded explanation from computed statistics."""
    if stats.get("highest_paying_job"):
        # Salary results use deterministic wording so benchmark values are never
        # replaced by an ungrounded model summary.
        return tools.fallback_explanation(plan, stats)
    if is_configured():
        try:
            system, user = tools.build_explain_prompt(metadata, plan, stats, request)
            data = call_llm_json(system, user)
            explanation = str(data.get("explanation") or "").strip()
            insights = data.get("insights")
            if isinstance(insights, list):
                insights = [str(i).strip() for i in insights if str(i).strip()]
            if explanation or insights:
                return explanation or "", (insights or [])[:6]
        except LLMError as exc:
            logger.error("LLM explanation failed, using fallback: %s", exc)
    return tools.fallback_explanation(plan, stats)


def execute_node(state: AgentState) -> dict:
    """Run the plan, render a chart when possible, and collect warnings."""
    chat_id = state.get("chat_id")
    df = store.get(chat_id, "df")
    if df is None:
        # Session data can disappear after a restart because the store is in memory.
        return {
            "error": (
                "The dataset is no longer available in this session. "
                "Please upload the file again."
            ),
        }

    plan = state.get("plan") or {}
    request = state.get("request", "")
    metadata = state.get("metadata") or {}

    try:
        # analyzer is the only layer allowed to perform Pandas calculations.
        result = analyzer.execute_plan(df, plan)
    except Exception as exc:
        logger.exception("analysis execution failed")
        return {"error": f"Analysis failed: {exc}"}

    chart_web = None
    if result.get("chart_type") != "table":
        # Rendering is isolated so a plotting failure can degrade to text/table data.
        try:
            fig = chart_gen.render(result.get("chart_data") or {})
            chart_web = chart_gen.save_figure(fig, chat_id)
        except Exception as exc:
            logger.exception("chart generation failed")
            result["warnings"] = list(result.get("warnings") or []) + [
                "The chart could not be rendered; showing a table insight instead."
            ]
            result["chart_data"] = {"kind": "table"}
            result["chart_type"] = "table"

    explanation, insights = _explain(metadata, plan, result.get("stats") or {}, request)
    warnings = list(state.get("warnings") or []) + list(result.get("warnings") or [])

    return {
        "result": result,
        "stats": result.get("stats"),
        "chart_type": result.get("chart_type"),
        "chart_web": chart_web,
        "explanation": explanation,
        "insights": insights,
        "warnings": warnings,
    }


def finalize_node(state: AgentState) -> dict:
    """Convert graph state into the stable message shape rendered by Jinja."""
    error = state.get("error")
    if error:
        # Keep errors in the same message list so the HTMX fragment can render them.
        bot = {
            "role": "assistant",
            "kind": "error",
            "text": error,
            "insights": [],
            "warnings": list(state.get("warnings") or []),
            "chart": None,
            "chart_type": None,
            "plan": None,
            "meta": None,
        }
        return {"bot_message": bot}

    result = state.get("result") or {}
    meta = state.get("metadata") or {}
    bot = {
        "role": "assistant",
        "kind": "result",
        "text": state.get("explanation") or "",
        "insights": list(state.get("insights") or []),
        "warnings": list(state.get("warnings") or []),
        "chart": state.get("chart_web"),
        "chart_type": result.get("chart_type"),
        "plan": state.get("plan"),
        "meta": {"file": meta.get("file_name"), "rows": meta.get("rows")},
    }
    return {"bot_message": bot}