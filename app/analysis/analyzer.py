from __future__ import annotations

import pandas as pd

PERIOD_FREQ = {
    "day": "D",
    "week": "W",
    "month": "ME",
    "quarter": "QE",
    "year": "YE",
}


def _to_numeric(df: pd.DataFrame, col: str) -> pd.Series:
    """Convert one planned measure to numeric values and coerce invalid cells."""
    return pd.to_numeric(df[col], errors="coerce")


def _top_categories(df: pd.DataFrame, plan: dict) -> tuple[list, list, list]:
    """Aggregate categorical data for pie charts, optionally by a measure."""
    cat_col = plan["x_column"]
    agg = plan.get("aggregation", "count")
    top_n = int(plan.get("top_n", 10))

    if agg in ("count",) or not plan.get("y_column"):
        # Count mode does not need a numeric measure; value_counts handles nulls
        # and produces chart-ready category totals.
        series = df[cat_col].dropna().value_counts()
        labels = series.head(top_n).index.map(str).tolist()
        values = [float(v) for v in series.head(top_n).tolist()]
        warnings = [
            f"{cat_col} contains {int(series.sum())} non-null values; "
            f"{(series > series.head(top_n).max()).sum() if len(series) > top_n else 0} categories beyond top {top_n} grouped as shown only."
        ] if len(series) > top_n else []
        return labels, values, warnings

    y_col = plan["y_column"]
    numeric = _to_numeric(df, y_col)
    grouped = numeric.groupby(df[cat_col]).agg(agg).sort_values(ascending=False)
    grouped = grouped.dropna()
    labels = grouped.head(top_n).index.map(str).tolist()
    values = [float(v) for v in grouped.head(top_n).tolist()]
    return labels, values, []


def _grouped_series(df: pd.DataFrame, plan: dict) -> tuple[pd.Series, list[str]]:
    """Create the grouped series used by line and bar charts."""
    x_col = plan["x_column"]
    y_col = plan["y_column"]
    agg = plan.get("aggregation", "sum")
    period = plan.get("group_by_period", "none")
    warnings: list[str] = []

    if pd.api.types.is_datetime64_any_dtype(df[x_col]) and period in PERIOD_FREQ:
        # Resampling gives time-series requests consistent day/week/month buckets.
        freq = PERIOD_FREQ[period]
        numeric = _to_numeric(df, y_col)
        ts = numeric.groupby(df[x_col]).agg(agg)
        ts = ts.sort_index()
        ts = ts.resample(freq).agg(agg)
        ts = ts.dropna()
        return ts, warnings

    if pd.api.types.is_datetime64_any_dtype(df[x_col]):
        warnings.append("No aggregation period was chosen; grouping by each unique date.")
        numeric = _to_numeric(df, y_col)
        ts = numeric.groupby(df[x_col]).agg(agg).sort_index().dropna()
        return ts, warnings

    # Non-date charts use the requested category and aggregation directly.
    grouped = df.groupby(x_col)[y_col].agg(agg).dropna()
    if plan.get("sort_values"):
        grouped = grouped.sort_values(ascending=False)
    return grouped, warnings


def execute_plan(df: pd.DataFrame, plan: dict) -> dict:
    """Execute a validated plan using predefined Pandas operations only."""
    chart_type = str(plan.get("chart_type", "bar")).lower()
    warnings: list[str] = []

    # This domain-specific path is deterministic and preserves every job rather
    # than applying the generic top-N chart behavior.
    if {
        "job_name",
        "salary_min_lpa",
        "salary_max_lpa",
        "average_salary_lpa",
    }.issubset(df.columns):
        return _salary_result(df, plan, warnings)

    if chart_type == "table" or chart_type == "none":
        return _table_result(df, plan, warnings)

    if chart_type == "histogram":
        return _histogram_result(df, plan, warnings)

    if chart_type == "scatter":
        return _scatter_result(df, plan, warnings)

    if chart_type == "pie":
        labels, values, warn = _top_categories(df, plan)
        warnings.extend(warn)
        chart_data = {
            "kind": "pie",
            "labels": labels,
            "values": values,
            "title": plan.get("chart_title", "Distribution"),
            "xlabel": plan.get("x_column") or "",
            "ylabel": plan.get("y_column") or "Share",
        }
        stats = _series_stats(values, plan.get("y_column") or "count")
        return _result(chart_data, stats, warnings, chart_type)

    grouped, warn = _grouped_series(df, plan)
    warnings.extend(warn)
    if grouped is None or len(grouped) == 0:
        return _table_result(df, plan, warnings + ["No data produced for the requested grouping."])

    labels = grouped.index.map(str).tolist()
    values = [float(v) for v in grouped.tolist()]
    chart_data = {
        "kind": chart_type,
        "labels": labels,
        "values": values,
        "title": plan.get("chart_title", ""),
        "xlabel": str(plan.get("x_column", "")),
        "ylabel": str(plan.get("y_column", "")),
    }
    stats = _series_stats(values, plan.get("y_column") or "value")
    stats["period"] = plan.get("group_by_period", "none")
    stats["x_column"] = plan.get("x_column")
    return _result(chart_data, stats, warnings, chart_type)


def _salary_result(df: pd.DataFrame, plan: dict, warnings: list[str]) -> dict:
    """Calculate the salary benchmark chart and all requested salary summaries."""
    warnings = list(warnings) + [
        "Salary figures are market benchmark ranges, not guaranteed salaries."
    ]
    salary = df.copy()
    for column in ("salary_min_lpa", "salary_max_lpa", "average_salary_lpa"):
        salary[column] = pd.to_numeric(salary[column], errors="coerce")
    # Rows without a usable job label or average cannot be represented in a bar.
    salary = salary.dropna(subset=["job_name", "average_salary_lpa"])
    salary = salary.sort_values("average_salary_lpa", ascending=False)
    if salary.empty:
        return _table_result(df, plan, warnings + ["No valid salary records were found."])

    labels = salary["job_name"].astype(str).tolist()
    values = salary["average_salary_lpa"].astype(float).tolist()
    chart_data = {
        "kind": "bar",
        "labels": labels,
        "values": values,
        "title": plan.get("chart_title") or "Average entry-level salary by job",
        "xlabel": "Job name",
        "ylabel": "Average salary (INR LPA)",
    }
    stats = {
        "column": "average_salary_lpa",
        "points": len(salary),
        "unit": "INR LPA",
        "highest_paying_job": labels[0],
        "highest_average_salary_lpa": values[0],
        "lowest_paying_job": labels[-1],
        "lowest_average_salary_lpa": values[-1],
        "overall_average_entry_level_salary_lpa": float(salary["average_salary_lpa"].mean()),
        "average_minimum_salary_lpa": float(salary["salary_min_lpa"].mean()),
        "average_maximum_salary_lpa": float(salary["salary_max_lpa"].mean()),
    }
    return _result(chart_data, stats, warnings, "bar")


def _histogram_result(df: pd.DataFrame, plan: dict, warnings: list[str]) -> dict:
    """Build histogram data from one numeric measure."""
    y_col = plan.get("y_column")
    if not y_col:
        y_col = plan.get("x_column")
    numeric = _to_numeric(df, y_col).dropna()
    if len(numeric) == 0:
        warnings.append("Nothing numeric to plot for a histogram.")
        chart_data = {"kind": "table", "columns": [], "rows": [], "title": "", "xlabel": "", "ylabel": ""}
        return _result(chart_data, {}, warnings, "histogram")
    chart_data = {
        "kind": "histogram",
        "values": [float(v) for v in numeric.tolist()],
        "bins": min(30, max(10, int(len(numeric) ** 0.5 * 2) + 1)),
        "title": plan.get("chart_title") or f"{y_col} distribution",
        "xlabel": y_col,
        "ylabel": "Frequency",
    }
    stats = _series_stats([float(v) for v in numeric.tolist()], y_col)
    quotes = [50, 90, 99]
    for q in quotes:
        stats[f"p{q}"] = round(float(numeric.quantile(q / 100)), 3)
    return _result(chart_data, stats, warnings, "histogram")


def _scatter_result(df: pd.DataFrame, plan: dict, warnings: list[str]) -> dict:
    """Build scatter data and an optional correlation summary."""
    x_col = plan.get("x_column")
    y_col = plan.get("y_column")
    x = _to_numeric(df, x_col)
    y = _to_numeric(df, y_col)
    mask = x.notna() & y.notna()
    if mask.sum() == 0:
        warnings.append("No overlapping numeric pairs for a scatter plot.")
        chart_data = {"kind": "table", "columns": [], "rows": [], "title": "", "xlabel": "", "ylabel": ""}
        return _result(chart_data, {}, warnings, "scatter")
    chart_data = {
        "kind": "scatter",
        "x": [float(v) for v in x[mask].tolist()],
        "y": [float(v) for v in y[mask].tolist()],
        "title": plan.get("chart_title") or f"{y_col} vs {x_col}",
        "xlabel": x_col,
        "ylabel": y_col,
    }
    stats = {
        "x_column": x_col,
        "y_column": y_col,
        "correlation": round(float(x[mask].corr(y[mask])), 4),
        "points": int(mask.sum()),
    }
    return _result(chart_data, stats, warnings, "scatter")


def _table_result(df: pd.DataFrame, plan: dict, warnings: list[str]) -> dict:
    """Return a bounded preview when a chart is unsuitable or empty."""
    cols = df.columns.tolist()[:5]
    rows = df.head(8).astype(object).where(df.head(8).notna(), None).to_dict(orient="records")
    chart_data = {
        "kind": "table",
        "columns": cols,
        "rows": rows,
        "title": plan.get("chart_title", "Data preview"),
        "xlabel": "",
        "ylabel": "",
    }
    stats = {
        "columns": cols,
        "rows": int(len(df)),
        "shown_rows": len(rows),
    }
    return _result(chart_data, stats, warnings, "table")


def _series_stats(values: list[float], label: str) -> dict:
    """Calculate common summaries shared by chart types."""
    series = pd.Series(values, dtype="float64")
    if len(series) == 0:
        return {"column": label, "points": 0}
    result = {
        "column": label,
        "points": int(len(series)),
        "sum": float(series.sum()),
        "mean": float(series.mean()),
        "min": float(series.min()),
        "max": float(series.max()),
        "median": float(series.median()),
    }
    if len(series) > 1 and result["min"] != result["max"]:
        result["first"] = float(series.iloc[0])
        result["last"] = float(series.iloc[-1])
        result["change_pct"] = round(
            ((result["last"] - result["first"]) / abs(result["first"]) * 100)
            if result["first"] != 0
            else 0.0,
            2,
        )
    return result


def _result(chart_data: dict, stats: dict, warnings: list[str], chart_type: str) -> dict:
    """Keep the stable result contract consumed by the agent and templates."""
    return {
        "chart_data": chart_data,
        "stats": stats,
        "warnings": warnings,
        "chart_type": chart_type,
    }