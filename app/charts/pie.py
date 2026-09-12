from __future__ import annotations

from .theme import PALETTE


def render(ax, data: dict) -> None:
    """Render category shares with percentages and a value legend."""
    labels = data.get("labels", [])
    values = data.get("values", [])
    colors = [PALETTE[i % len(PALETTE)] for i in range(len(values))]
    wedges, _, autotexts = ax.pie(
        values,
        labels=labels,
        colors=colors,
        autopct=lambda pct: f"{pct:.1f}%" if pct >= 2 else "",
        startangle=90,
        counterclock=False,
        pctdistance=0.78,
    )
    for text in autotexts:
        text.set_fontsize(8)
    ax.legend(
        wedges,
        [f"{l} ({v:g})" for l, v in zip(labels, values)],
        loc="center left",
        bbox_to_anchor=(1.0, 0.5),
        fontsize=8,
    )
    ax.set_title(data.get("title", ""), fontsize=13)