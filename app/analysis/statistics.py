from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd


def _is_missing(value: Any) -> bool:
    """Check scalar missingness without treating array results as booleans."""
    if value is None:
        return True
    missing = pd.isna(value)
    return isinstance(missing, (bool, np.bool_)) and bool(missing)


def _py_value(value: Any) -> Any:
    """Convert Pandas/NumPy/nested values into JSON-safe Python values."""
    if _is_missing(value):
        return None
    # Recurse through nested JSON values because pd.isna(list) returns an array.
    if isinstance(value, dict):
        return {str(key): _py_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_py_value(item) for item in value]
    if isinstance(value, np.ndarray):
        return [_py_value(item) for item in value.tolist()]
    if isinstance(value, np.generic):
        return _py_value(value.item())
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, float):
        if math.isnan(value):
            return None
        if math.isinf(value):
            return None
        return value
    return value


def _unique_count(series: pd.Series) -> int:
    """Count unique values, including unhashable nested JSON values."""
    try:
        return int(series.nunique(dropna=True))
    except TypeError:
        # Lists and dictionaries cannot be hashed by Pandas; their normalized
        # representations still provide stable metadata counts.
        values = {
            repr(_py_value(value))
            for value in series
            if not _is_missing(value)
        }
        return len(values)


def _unique_values(series: pd.Series, limit: int) -> list[str]:
    """Return a small de-duplicated display sample for a column."""
    values: list[str] = []
    seen: set[str] = set()
    for value in series:
        if _is_missing(value):
            continue
        normalized = _py_value(value)
        key = repr(normalized)
        if key in seen:
            continue
        seen.add(key)
        values.append(str(normalized))
        if len(values) >= limit:
            break
    return values


def _is_scalar_series(series: pd.Series) -> bool:
    """Identify columns that can safely be used as chart grouping labels."""
    return all(
        not isinstance(value, (dict, list, tuple, set, np.ndarray))
        for value in series
        if not _is_missing(value)
    )


def numeric_statistics(df: pd.DataFrame, cols: list[str], sample: int = 10) -> dict:
    """Calculate bounded numeric summaries for the planner context."""
    stats: dict[str, dict] = {}
    selected = cols[:sample]
    for col in selected:
        series = pd.to_numeric(df[col], errors="coerce").dropna()
        if len(series) == 0:
            stats[col] = {"errors": "no numeric values"}
            continue
        stats[col] = {
            "min": float(series.min()),
            "mean": float(series.mean()),
            "median": float(series.median()),
            "max": float(series.max()),
            "std": float(series.std()) if len(series) > 1 else 0.0,
            "sum": float(series.sum()),
            "non_null": int(series.notna().sum()),
            "null": int(series.isna().sum()),
        }
    return stats


def build_metadata(df: pd.DataFrame, filename: str) -> dict:
    """Build the metadata-only dataset description sent to the agent/LLM."""
    # The LLM receives schema and summaries, never the full uploaded dataset.
    numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    datetime_cols = [
        c for c in df.columns if pd.api.types.is_datetime64_any_dtype(df[c])
    ]
    object_cols = [
        c for c in df.columns if pd.api.types.is_string_dtype(df[c])
    ]
    other_cols = [
        c
        for c in df.columns
        if c not in numeric_cols and c not in datetime_cols and c not in object_cols
    ]
    categorical_cols = []
    for col in object_cols:
        uniques = _unique_count(df[col])
        if uniques <= 500 and _is_scalar_series(df[col]):
            categorical_cols.append(col)

    # Five normalized rows help the planner understand values without exposing
    # the entire file to the model.
    sample_rows = (
        df.head(5)
        .map(_py_value)
        .to_dict(orient="records")
    )

    return {
        "file_name": filename,
        "rows": int(len(df)),
        "columns": [
            {
                "name": col,
                "dtype": str(df[col].dtype),
                "nulls": int(df[col].isna().sum()),
                "unique": _unique_count(df[col]),
            }
            for col in df.columns
        ],
        "numeric_columns": numeric_cols,
        "categorical_columns": categorical_cols,
        "datetime_columns": datetime_cols,
        "other_columns": other_cols,
        "numeric_statistics": numeric_statistics(df, numeric_cols),
        "unique_values": {
            col: _unique_values(df[col], 8)
            for col in categorical_cols[:6]
        },
        "sample_rows": sample_rows,
    }