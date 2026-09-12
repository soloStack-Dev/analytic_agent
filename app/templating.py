from __future__ import annotations

from fastapi.templating import Jinja2Templates

from .config import TEMPLATE_DIR

# One shared environment keeps filters and template configuration consistent
# across normal pages and HTMX fragments.
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))


def _short_ts(value: str | None) -> str:
    """Render ISO timestamps compactly in the chat history and message headers."""
    if not value:
        return ""
    return str(value)[:16].replace("T", " ")


templates.env.filters["short_ts"] = _short_ts