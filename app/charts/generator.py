from __future__ import annotations

import uuid

import matplotlib

matplotlib.use("Agg")

from ..config import GENERATED_DIR  # noqa: E402
from .theme import PALETTE  # noqa: E402

from . import bar, histogram, line, pie, scatter  # noqa: E402, F401

RENDERERS = {
    "bar": bar.render,
    "line": line.render,
    "pie": pie.render,
    "scatter": scatter.render,
    "histogram": histogram.render,
}


def render(chart_data: dict):
    """Create a Matplotlib figure from the analyzer's chart-data contract."""
    kind = chart_data.get("kind", "table")
    if kind == "table":
        # Tables are rendered by the HTML response; no image should be created.
        return None

    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(11, 6), dpi=110)
    try:
        # Unknown kinds degrade to a bar chart instead of crashing the request.
        if kind in RENDERERS:
            RENDERERS[kind](ax, chart_data)
        else:
            RENDERERS["bar"](ax, chart_data)
    except Exception:
        plt.close(fig)
        raise

    title = chart_data.get("title") or ""
    ax.set_title(title, fontsize=13, pad=14)
    if chart_data.get("xlabel"):
        ax.set_xlabel(chart_data["xlabel"])
    if chart_data.get("ylabel"):
        ax.set_ylabel(chart_data["ylabel"])

    fig.tight_layout()
    return fig


def save_figure(fig, chat_id: str) -> str | None:
    """Save a figure under a generated server filename and always close it."""
    if fig is None:
        return None
    try:
        # The random suffix prevents concurrent analyses from overwriting images.
        filename = f"{chat_id}-{uuid.uuid4().hex[:8]}.png"
        fig.savefig(GENERATED_DIR / filename, bbox_inches="tight")
        return f"/generated/{filename}"
    finally:
        import matplotlib.pyplot as plt

        plt.close(fig)