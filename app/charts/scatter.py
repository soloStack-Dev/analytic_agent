from __future__ import annotations

from .theme import PALETTE


def render(ax, data: dict) -> None:
    """Render numeric pairs and a best-fit guide when enough points exist."""
    x = data.get("x", [])
    y = data.get("y", [])
    ax.scatter(x, y, s=18, color=PALETTE[2], alpha=0.7)
    if len(x) > 3:
        # A trend line is informative only when the sample has more than three pairs.
        try:
            import numpy as np

            slope, intercept = np.polyfit(x, y, 1)
            xs = [min(x), max(x)]
            ax.plot(xs, [slope * v + intercept for v in xs], color=PALETTE[3], linestyle="--", linewidth=1.5)
        except Exception:
            pass
    ax.grid(linestyle="--", alpha=0.35)