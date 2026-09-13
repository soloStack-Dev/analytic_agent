from __future__ import annotations

import os
import tempfile
from pathlib import Path

from dotenv import load_dotenv

# Resolve every runtime directory from the repository root so the app behaves
# consistently whether it is started from VS Code, Uvicorn, or a task runner.
BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")

APP_DIR = Path(__file__).resolve().parent
TEMPLATE_DIR = APP_DIR / "templates"
STATIC_DIR = APP_DIR / "static"
HTMX_DIST_DIR = BASE_DIR / "node_modules" / "htmx.org" / "dist"

# Vercel's deployed application bundle is read-only. Detect both its standard
# environment variables and its /var/task bundle path for runtime compatibility.
IS_VERCEL = (
    os.getenv("VERCEL", "").lower() == "1"
    or bool(os.getenv("VERCEL_ENV"))
    or BASE_DIR.as_posix().startswith("/var/task")
)
RUNTIME_DIR = (
    Path(tempfile.gettempdir()) / "chart-agent"
    if IS_VERCEL
    else BASE_DIR
)

UPLOAD_DIR = RUNTIME_DIR / "uploads"
GENERATED_DIR = RUNTIME_DIR / "generated"
DATA_DIR = RUNTIME_DIR / "data"
LOGS_DIR = RUNTIME_DIR / "logs"

# Runtime folders are created during startup because a fresh checkout does not
# contain generated charts, uploaded files, or the history database yet.
for _dir in (UPLOAD_DIR, GENERATED_DIR, DATA_DIR, LOGS_DIR):
    _dir.mkdir(parents=True, exist_ok=True)

CHAT_DB_FILE = DATA_DIR / "chats.json"

# Keep the limit in bytes because uploads are counted while streaming chunks.
MAX_UPLOAD_SIZE = int(os.getenv("MAX_UPLOAD_MB", "10")) * 1024 * 1024
ALLOWED_EXTENSIONS = {"csv", "json", "xlsx", "xls"}

_open_router_key = os.getenv("OPEN_ROUTER_API_KEY", "").strip()
_open_router_model = os.getenv("OPEN_ROUTER_MODEL", "").strip()

# Generic LLM variables take precedence over the OpenRouter convenience pair.
LLM_PROVIDER = (
    os.getenv("LLM_PROVIDER", "").strip().lower()
    or ("openrouter" if _open_router_key or _open_router_model else "openai")
)
LLM_API_KEY = os.getenv("LLM_API_KEY", "").strip() or _open_router_key
LLM_MODEL = os.getenv("LLM_MODEL", "").strip() or _open_router_model
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "").strip()
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.2"))
LLM_TIMEOUT = float(os.getenv("LLM_TIMEOUT", "60"))

HISTORY_PAGE_SIZE = 50