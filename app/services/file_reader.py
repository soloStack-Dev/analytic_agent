from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .llm import LLMError


class FileReadError(Exception):
    """Raised when an uploaded data file cannot be parsed safely."""

    pass


def read_json(path: Path) -> pd.DataFrame:
    """Read JSON arrays, column-oriented objects, or objects with ``records``."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
    except UnicodeDecodeError:
        raw = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except json.JSONDecodeError as exc:
        raise FileReadError(f"Invalid JSON: {exc}") from exc

    if isinstance(raw, list):
        # A JSON array of objects is already the row-oriented shape Pandas expects.
        return pd.DataFrame(raw)
    if isinstance(raw, dict):
        records = raw.get("records")
        if isinstance(records, list) and all(isinstance(record, dict) for record in records):
            # Dataset wrappers often keep descriptive fields beside the real rows;
            # analyze the records array instead of treating the wrapper as one row.
            return pd.json_normalize(records)
        if all(isinstance(v, list) for v in raw.values()):
            # Support the column-oriented JSON form: {"column": [values, ...]}.
            try:
                return pd.DataFrame(raw)
            except ValueError as exc:
                raise FileReadError(
                    f"JSON columns have inconsistent lengths: {exc}"
                ) from exc
        # Preserve a single object as one row when it has no record collection.
        try:
            return pd.json_normalize(raw)
        except Exception as exc:
            return pd.DataFrame([raw])
    raise FileReadError("JSON must be an object or an array of objects")


def _add_derived_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Add known measures that are deterministic transformations of source data."""
    required = {"salary_min_lpa", "salary_max_lpa"}
    if required.issubset(df.columns) and "average_salary_lpa" not in df.columns:
        # Coercion makes malformed values become NaN, allowing normal analysis
        # filtering to exclude only invalid rows instead of rejecting the file.
        minimum = pd.to_numeric(df["salary_min_lpa"], errors="coerce")
        maximum = pd.to_numeric(df["salary_max_lpa"], errors="coerce")
        df["average_salary_lpa"] = (minimum + maximum) / 2
    return df


def load_dataframe(path: Path) -> pd.DataFrame:
    """Load, normalize, and clean one supported upload format."""
    ext = path.suffix.lower().lstrip(".")
    try:
        # Select the parser from the trusted server-side extension, never from
        # executable content inside the uploaded file.
        if ext == "csv":
            df = pd.read_csv(path)
        elif ext == "json":
            df = read_json(path)
        elif ext == "xlsx":
            df = pd.read_excel(path, engine="openpyxl")
        elif ext == "xls":
            df = pd.read_excel(path, engine="xlrd")
        else:
            raise FileReadError(f"Unsupported file type: {ext}")
    except FileReadError:
        raise
    except LLMError:
        raise
    except Exception as exc:
        raise FileReadError(f"Could not parse file: {exc}") from exc

    if df is None or len(df) == 0:
        raise FileReadError("The file does not contain any rows")
    # Normalize column labels once so planner requests can resolve them reliably.
    df.columns = [str(col).strip() for col in df.columns]
    df = df.loc[:, ~df.columns.duplicated(keep="first")]
    from ..analysis.cleaner import clean

    return _add_derived_columns(clean(df))