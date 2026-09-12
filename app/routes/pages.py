from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from ..services import history as chat_db
from ..templating import templates

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def home(request: Request):
    """Render the public entry page."""
    return templates.TemplateResponse(request, "index.html", {})


@router.get("/chat", response_class=HTMLResponse)
def chat_page(request: Request):
    """Open the current cookie-selected chat or create the first chat."""
    chat_id = request.cookies.get("chat_id")
    chat = chat_db.get_chat(chat_id) if chat_id else None
    if chat is None:
        # The browser always receives a valid chat ID for subsequent HTMX requests.
        chat = chat_db.create_chat()
        chat_id = chat["id"]
    response = templates.TemplateResponse(
        request,
        "chat.html",
        {
            "chat": chat,
            "chat_id": chat_id,
            "chats": chat_db.list_chats(),
        },
    )
    response.set_cookie("chat_id", chat_id)
    return response


@router.get("/chat/new")
def new_chat(request: Request):
    """Create a blank chat and select it through the browser cookie."""
    chat = chat_db.create_chat()
    response = RedirectResponse(url="/chat", status_code=303)
    response.set_cookie("chat_id", chat["id"])
    return response


@router.get("/api/history", response_class=HTMLResponse)
def history_panel(request: Request):
    """Return the reusable history fragment for the modal/sidebar."""
    return templates.TemplateResponse(
        request,
        "partials/history_items.html",
        {"chats": chat_db.list_chats(), "chat_id": request.cookies.get("chat_id", "")},
    )


@router.delete("/api/chat/{chat_id}", status_code=204)
def delete_chat(request: Request, chat_id: str):
    """Delete one persisted chat; HTMX removes its row after the 204 response."""
    chat_db.delete_chat(chat_id)
    return Response(status_code=204)


@router.get("/api/chat/{chat_id}/messages", response_class=HTMLResponse)
def load_chat_messages(request: Request, chat_id: str):
    """Return stored messages and select the requested chat in the browser."""
    chat = chat_db.get_chat(chat_id)
    if chat is None:
        # A stale history link should recover by creating a valid new chat.
        chat = chat_db.create_chat()
        chat_id = chat["id"]
    response = templates.TemplateResponse(
        request,
        "partials/messages.html",
        {
            "chat_id": chat_id,
            "msgs": chat.get("messages", []),
            "chats": chat_db.list_chats(),
        },
    )
    response.set_cookie("chat_id", chat_id)
    return response