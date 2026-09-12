from __future__ import annotations

from .theme import PALETTE


def render(ax, data: dict) -> None:
    """Render a numeric distribution using the requested number of bins."""
    values = data.get("values", [])
    bins = int(data.get("bins", 20))
    ax.hist(values, bins=bins, color=PALETTE[4], alpha=0.85, edgecolor="white")
    ax.grid(axis="y", linestyle="--", alpha=0.35)