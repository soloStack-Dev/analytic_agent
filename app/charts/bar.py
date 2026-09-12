from __future__ import annotations

from .theme import PALETTE


def render(ax, data: dict) -> None:
    """Render categorical labels and numeric values as annotated bars."""
    labels = data.get("labels", [])
    values = data.get("values", [])
    # Keep the value labels on the bars so the chart remains readable without hover.
    bars = ax.bar(labels, values, color=PALETTE[0], alpha=0.9, edgecolor="white")
    for bar, value in zip(bars, values):
        ax.annotate(
            f"{value:g}",
            xy=(bar.get_x() + bar.get_width() / 2, bar.get_height()),
            xytext=(0, 3),
            textcoords="offset points",
            ha="center",
            fontsize=8,
        )
    ax.tick_params(axis="x", rotation=35)
    ax.grid(axis="y", linestyle="--", alpha=0.35)