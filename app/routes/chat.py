from __future__ import annotations

import time

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse

from ..logger import logger
from ..services import history as chat_db
from ..services.session_store import store
from ..templating import templates
from .analysis import analyze_chat
from .upload import cleanup_previous, persist_upload, safe_original_name

router = APIRouter()

_last_request: dict[str, float] = {}


def _rate_limit(request: Request) -> None:
    """Apply a small per-process cooldown to protect the synchronous workflow."""
    ip = request.client.host if request.client else "unknown"
    now = time.monotonic()
    previous = _last_request.get(ip, 0.0)
    # This lightweight guard is sufficient for a single worker; shared deployments
    # should replace it with a shared store such as Redis.
    if now - previous < 0.5:
        raise HTTPException(status_code=429, detail="Too many messages. Please wait a second.")
    _last_request[ip] = now


def _rejected_fragment(
    request: Request,
    chat_id: str,
    user_text: str,
    file_name: str | None,
    detail: str,
) -> HTMLResponse:
    """Render an upload validation error in the normal chat message shape."""
    return templates.TemplateResponse(
        request,
        "partials/messages.html",
        {
            "chat_id": chat_id,
            "msgs": [
                {
                    "role": "user",
                    "kind": "text",
                    "text": user_text,
                    "file": file_name,
                },
                {
                    "role": "assistant",
                    "kind": "error",
                    "text": f"File rejected: {detail}",
                    "insights": [],
                    "warnings": [],
                    "chart": None,
                    "chart_type": None,
                    "plan": None,
                    "meta": None,
                },
            ],
        },
    )


@router.post("/api/chat", response_class=HTMLResponse, dependencies=[Depends(_rate_limit)])
async def chat_endpoint(
    request: Request,
    message: str = Form(""),
    file: UploadFile | None = File(None),
    chat_id: str = Form(""),
):
    """Accept a message/upload, run analysis, persist both messages, and render HTMX."""
    # Existing chat IDs continue a conversation; an unknown or empty ID starts one.
    chat = chat_db.get_chat(chat_id) or chat_db.create_chat()
    chat_id = chat["id"]

    user_text = message.strip()
    upload_path = None
    original_name = None
    if file is not None and file.filename:
        # Upload validation happens before the agent sees a path or filename.
        try:
            upload_path = persist_upload(file)
            cleanup_previous(store.get(chat_id, "upload_path"))
            store.set(chat_id, "upload_path", str(upload_path))
            original_name = safe_original_name(file.filename)
        except HTTPException as exc:
            return _rejected_fragment(
                request, chat_id, user_text, safe_original_name(file.filename), str(exc.detail)
            )

    # An upload without a question still gets a useful default analysis request.
    request_text = user_text or "Analyze this dataset."
    try:
        bot_message = analyze_chat(
            chat_id,
            request_text,
            str(upload_path) if upload_path else None,
            original_name,
        )
    except Exception as exc:
        logger.exception("agent invocation failed")
        bot_message = {
            "role": "assistant",
            "kind": "error",
            "text": f"Something went wrong while analyzing: {exc}",
            "insights": [],
            "warnings": [],
            "chart": None,
            "chart_type": None,
            "plan": None,
            "meta": None,
        }

    # Persist the exact user/bot pair so history reloads reproduce the response.
    user_payload = {
        "role": "user",
        "kind": "text",
        "text": user_text,
        "file": original_name,
    }
    stored_user = chat_db.append_message(chat_id, user_payload)
    stored_bot = chat_db.append_message(chat_id, bot_message)
    chat_db.touch_chat(chat_id, user_text or "File upload chat")

    msgs = [stored_user, stored_bot]
    return templates.TemplateResponse(
        request,
        "partials/messages.html",
        {
            "chat_id": chat_id,
            "msgs": msgs,
            "chats": chat_db.list_chats(),
        },
    )