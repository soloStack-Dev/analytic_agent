from __future__ import annotations

import json

# These values form the allow-list used by both prompts and plan validation.
CHART_TYPES = ["line", "bar", "pie", "scatter", "histogram", "table"]
AGGREGATIONS = ["sum", "mean", "median", "min", "max", "count"]
PERIODS = ["day", "week", "month", "quarter", "year", "none"]


def _resolve_column(name: str | None, available: list[str]) -> str | None:
    """Resolve a model-provided column name without trusting arbitrary names."""
    if not name:
        return None
    name = str(name).strip()
    exact = [c for c in available if c == name]
    if exact:
        return exact[0]
    lowered = name.lower()
    case = [c for c in available if c.lower() == lowered]
    if case:
        return case[0]
    for c in available:
        if lowered in c.lower() or c.lower() in lowered:
            return c
    return None


def _first(cls: str, metadata: dict) -> str | None:
    """Return the first column in a metadata category, if one exists."""
    cols = metadata.get(f"{cls}_columns") or []
    return cols[0] if cols else None


def validate_plan(raw: dict, metadata: dict) -> tuple[dict, list[str]]:
    """Normalize an untrusted model plan into a safe executable plan."""
    warnings: list[str] = []
    numeric = metadata.get("numeric_columns") or []
    categorical = metadata.get("categorical_columns") or []
    datetime_cols = metadata.get("datetime_columns") or []
    all_cols = [c["name"] for c in metadata.get("columns", [])]

    chart_type = str(raw.get("chart_type", "")).strip().lower()
    # Unknown chart types never reach the executor.
    if chart_type not in CHART_TYPES:
        chart_type = "bar"

    x_column = _resolve_column(raw.get("x_column"), all_cols)
    y_column = _resolve_column(raw.get("y_column"), all_cols)

    if raw.get("x_column") and x_column is None:
        warnings.append(f"Column '{raw.get('x_column')}' was not found; using a suitable column instead.")
    if raw.get("y_column") and y_column is None:
        warnings.append(f"Column '{raw.get('y_column')}' was not found; using a suitable column instead.")

    if chart_type in ("line", "bar"):
        # Line and bar charts need a grouping dimension and usually a numeric value.
        if y_column is None:
            y_column = _first("numeric", metadata)
        if x_column is None:
            x_column = _first("datetime", metadata) or _first("categorical", metadata)
        if x_column is None:
            chart_type = "table"
            warnings.append("No grouping column found; showing a table insight instead.")
        if y_column is None:
            chart_type = "table"
            warnings.append("No numeric column found; showing a table insight instead.")
    elif chart_type == "pie":
        if x_column is None:
            x_column = _first("categorical", metadata) or _first("datetime", metadata)
        if x_column is None:
            chart_type = "table"
            warnings.append("No categorical column found; showing a table insight instead.")
    elif chart_type == "scatter":
        if y_column is None:
            y_column = _first("numeric", metadata)
        if x_column is None:
            candidates = [c for c in numeric if c != y_column]
            x_column = candidates[0] if candidates else y_column
        if y_column is None or x_column is None:
            chart_type = "table"
            warnings.append("Not enough numeric columns for a scatter plot; showing a table instead.")
    elif chart_type == "histogram":
        if y_column is None:
            y_column = _first("numeric", metadata)
        if y_column is not None and y_column not in numeric:
            x_column, y_column = y_column, None
            if y_column is None:
                y_column = _first("numeric", metadata)
        if y_column is None:
            chart_type = "table"
            warnings.append("No numeric column found for a histogram; showing a table instead.")

    # Invalid aggregation and period values fall back to known Pandas operations.
    aggregation = str(raw.get("aggregation", "sum")).strip().lower()
    if aggregation not in AGGREGATIONS:
        aggregation = "sum"

    period = str(raw.get("group_by_period", "none")).strip().lower()
    if period not in PERIODS:
        period = "none"
    if chart_type in ("line",) and x_column in datetime_cols and period == "none":
        period = "month"

    try:
        top_n = min(20, max(3, int(raw.get("top_n", 10))))
    except (TypeError, ValueError):
        top_n = 10

    plan = {
        "chart_type": chart_type,
        "x_column": x_column,
        "y_column": y_column,
        "aggregation": aggregation,
        "group_by_period": period,
        "top_n": top_n,
        "chart_title": str(raw.get("chart_title", "") or "").strip(),
        "explanation_plan": str(raw.get("explanation_plan", "") or "").strip(),
    }
    if plan["chart_type"] == "line" and x_column in datetime_cols:
        plan["chart_title"] = plan["chart_title"] or f"{y_column} over {x_column}"
    if not plan["chart_title"] and x_column:
        plan["chart_title"] = f"{y_column} by {x_column}".strip(" by ")

    return plan, warnings


def heuristic_plan(metadata: dict, request: str) -> dict:
    """Select a useful chart without an LLM by inspecting schema categories."""
    numeric = metadata.get("numeric_columns") or []
    categorical = metadata.get("categorical_columns") or []
    datetime_cols = metadata.get("datetime_columns") or []
    request = (request or "").lower()

    raw: dict = {"chart_type": "bar", "aggregation": "sum", "group_by_period": "none", "top_n": 10}
    y_column = _first("numeric", metadata)
    x_column = None

    if datetime_cols:
        # Time columns are the strongest signal for a trend chart.
        x_column = datetime_cols[0]
        raw["chart_type"] = "line"
        raw["group_by_period"] = "month"
    elif "distribution" in request or "share" in request or "top" in request:
        if categorical:
            x_column = categorical[0]
            raw["chart_type"] = "pie"
    elif categorical:
        x_column = categorical[0]
        if not y_column:
            raw["chart_type"] = "pie"
    else:
        x_column = None

    if y_column and not x_column and raw["chart_type"] == "bar":
        pass

    if raw["chart_type"] != "pie" and not y_column and not x_column:
        raw["chart_type"] = "table"

    if y_column and any(k in request for k in ["histogram", "distribution of " + y_column.lower()]):
        raw["chart_type"] = "histogram"
        raw["x_column"] = None
        raw["y_column"] = y_column
        return validate_plan(raw, metadata)[0]

    raw["x_column"] = x_column
    raw["y_column"] = y_column
    raw["chart_title"] = ""
    raw["explanation_plan"] = "Rule-based fallback plan."
    if raw["chart_type"] == "pie":
        raw["y_column"] = None
    return validate_plan(raw, metadata)[0]


def build_plan_prompt(metadata: dict, request: str) -> tuple[str, str]:
    """Build the planner prompt from metadata and the user's natural-language ask."""
    system = (
        "You are the planning module of an AI data analyst. You NEVER run or propose code. "
        "You inspect dataset metadata and produce a small structured analysis plan as JSON. "
        f"Available chart types: {', '.join(CHART_TYPES)}. "
        f"Available aggregations: {', '.join(AGGREGATIONS)}. "
        f"Available time periods: {', '.join(PERIODS)}. "
        "Respond ONLY with a JSON object, keys: "
        'chart_type, x_column (or null), y_column (or null), aggregation, '
        'group_by_period, top_n (int 3-20), chart_title (short), explanation_plan (one sentence). '
        "Prefer a line chart when the request asks for a trend over time. "
        "When the request cannot be plotted, use chart_type 'table'."
    )
    user = (
        "DATASET METADATA (JSON):\n"
        + json.dumps(metadata, ensure_ascii=False, default=str)
        + "\n\nUSER REQUEST: "
        + request
    )
    return system, user


def build_explain_prompt(metadata: dict, plan: dict, stats: dict, request: str) -> tuple[str, str]:
    """Build a grounded explanation prompt using computed statistics only."""
    system = (
        "You are the explanation module of an AI data analyst. Using the plan and computed statistics, "
        "write a short explanation and up to 4 concise insight bullets for a non-technical user. "
        "Do not invent numbers outside the provided statistics. "
        'Respond ONLY with JSON: {"explanation": "1-3 sentences", "insights": ["bullet", "..."]}.'
    )
    user = (
        "USER REQUEST: "
        + request
        + "\n\nPLAN (JSON):\n"
        + json.dumps(plan, ensure_ascii=False, default=str)
        + "\n\nCOMPUTED STATISTICS (JSON):\n"
        + json.dumps(stats, ensure_ascii=False, default=str)
    )
    return system, user


def fallback_explanation(plan: dict, stats: dict) -> tuple[str, list[str]]:
    """Return a deterministic explanation when the model is unavailable."""
    if stats.get("highest_paying_job"):
        unit = stats.get("unit", "INR LPA")
        explanation = (
            "I normalized the job records, calculated each average salary as "
            "(minimum + maximum) / 2, and sorted the benchmark ranges from "
            "highest to lowest. These figures are market benchmarks, not guaranteed salaries."
        )
        insights = [
            f"Highest-paying benchmark: {stats['highest_paying_job']} at {stats['highest_average_salary_lpa']:g} {unit}.",
            f"Lowest-paying benchmark: {stats['lowest_paying_job']} at {stats['lowest_average_salary_lpa']:g} {unit}.",
            f"Overall average entry-level salary: {stats['overall_average_entry_level_salary_lpa']:g} {unit}.",
            f"Average minimum salary: {stats['average_minimum_salary_lpa']:g} {unit}; average maximum salary: {stats['average_maximum_salary_lpa']:g} {unit}.",
        ]
        return explanation, insights

    y = stats.get("column") or plan.get("y_column") or "value"
    kind = plan.get("chart_type", "chart")
    explanation = f"I aggregated the relevant data and produced a {kind} chart."
    if stats.get("points"):
        explanation = (
            f"Across {stats['points']} data points, the {y} series "
            f"ranges from {stats.get('min'):g} to {stats.get('max'):g} "
            f"with an average of {stats.get('mean'):g}."
        )
    insights: list[str] = []
    if stats.get("sum") is not None and stats.get("points", 0) > 1:
        insights.append(f"Total {y}: {stats['sum']:g}.")
    if stats.get("max") is not None and stats.get("points", 0) > 1:
        insights.append(f"Peak value of {y}: {stats['max']:g}.")
    if stats.get("change_pct") is not None:
        direction = "up" if stats["change_pct"] >= 0 else "down"
        insights.append(
            f"From first to last point the series moved {direction} by {abs(stats['change_pct']):g}%."
        )
    if stats.get("correlation") is not None:
        corr = stats["correlation"]
        insights.append(
            f"Correlation between the plotted variables is {corr:+.2f} "
            + ("(moderate or stronger)." if abs(corr) >= 0.5 else "(weak).")
        )
    if not insights:
        insights.append("The data was summarized using the requested aggregation.")
    return explanation, insights