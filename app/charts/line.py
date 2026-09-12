from __future__ import annotations

from .theme import PALETTE


def render(ax, data: dict) -> None:
    """Render an ordered series with point labels and a readable x-axis."""
    labels = data.get("labels", [])
    values = data.get("values", [])
    ax.plot(labels, values, marker="o", color=PALETTE[1], linewidth=2)
    for x, y in zip(labels, values):
        ax.annotate(
            f"{y:g}",
            xy=(x, y),
            xytext=(0, 5),
            textcoords="offset points",
            ha="center",
            fontsize=8,
        )
    ax.tick_params(axis="x", rotation=35)
    ax.grid(axis="y", linestyle="--", alpha=0.35)