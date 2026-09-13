from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import GENERATED_DIR, HTMX_DIST_DIR, STATIC_DIR
from .logger import logger
from .routes import chart, chat, pages

app = FastAPI(title="AI Data Analyst", version="0.1.0")

# Static assets, generated charts, and HTMX are mounted explicitly; uploads are
# intentionally not mounted because they must never be served as files.
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.mount("/htmx", StaticFiles(directory=str(HTMX_DIST_DIR)), name="htmx")
app.mount("/generated", StaticFiles(directory=str(GENERATED_DIR)), name="generated")

app.include_router(pages.router)
app.include_router(chat.router)
app.include_router(chart.router)


@app.get("/favicon.ico", include_in_schema=False)
@app.get("/favicon.png", include_in_schema=False)
def favicon() -> FileResponse:
    """Serve legacy favicon URLs from the single maintained favicon asset."""
    return FileResponse(STATIC_DIR / "favicon.svg", media_type="image/svg+xml")


@app.get("/health")
def health():
    """Provide a lightweight process health check for local/proxy monitoring."""
    return {"status": "ok"}


logger.info("AI Data Analyst started")