from __future__ import annotations

import pandas as pd

# Column names containing these words are strong date candidates; other columns
# are parsed only when most sampled values can be interpreted as dates.
_DATE_KEYWORDS = ("date", "time", "day", "month", "year", "period", "fecha")


def _looks_like_date(series: pd.Series) -> bool:
    """Return whether a column has enough date-like values to convert safely."""
    name = str(series.name).strip().lower()
    if any(k in name for k in _DATE_KEYWORDS):
        # Keyword columns may be sparse, so use a larger sample and an 80% threshold.
        sample = series.dropna().head(50)
        parsed = pd.to_datetime(sample, errors="coerce", format="mixed")
        if parsed.notna().mean() >= 0.8:
            return True
        return False
    # For unnamed date columns require stronger evidence to avoid converting IDs.
    sample = series.dropna().head(20)
    if len(sample) < 3:
        return False
    parsed = pd.to_datetime(sample.astype(str), errors="coerce", format="mixed")
    return parsed.notna().mean() >= 0.9


def clean(df: pd.DataFrame) -> pd.DataFrame:
    """Remove unusable columns and normalize date values without mutating input."""
    df = df.copy()
    # Empty columns and duplicate labels add ambiguity without analytical value.
    df = df.dropna(axis=1, how="all")
    df = df.loc[:, ~df.columns.duplicated(keep="first")]

    for col in df.columns:
        # Preserve dates already parsed by the source reader.
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            continue
        if _looks_like_date(df[col]):
            df[col] = pd.to_datetime(df[col], errors="coerce")

    # A fresh integer index makes later row-oriented JSON/chart output predictable.
    df = df.reset_index(drop=True)
    return df