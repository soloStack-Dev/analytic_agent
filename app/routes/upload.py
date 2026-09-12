from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile

from ..config import ALLOWED_EXTENSIONS, MAX_UPLOAD_SIZE, UPLOAD_DIR


def persist_upload(file: UploadFile) -> Path:
    """Validate and stream an uploaded file into the private uploads directory."""
    original = Path(file.filename or "file")
    ext = original.suffix.lower().lstrip(".")
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '.{ext}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    target = UPLOAD_DIR / f"{uuid.uuid4().hex}.{ext}"
    size = 0
    try:
        with target.open("wb") as out:
            while True:
                # Streaming avoids loading an attacker-controlled file into memory.
                chunk = file.file.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_UPLOAD_SIZE:
                    # Remove a partial file before returning the validation error.
                    raise HTTPException(
                        status_code=413,
                        detail=f"File exceeds the {MAX_UPLOAD_SIZE // (1024 * 1024)} MB limit",
                    )
                out.write(chunk)
    except HTTPException:
        target.unlink(missing_ok=True)
        raise

    return target


def cleanup_previous(path: str | None) -> None:
    """Delete the previous temporary upload when a chat receives a replacement."""
    if not path:
        return
    try:
        Path(path).unlink(missing_ok=True)
    except OSError:
        pass


def safe_original_name(filename: str | None) -> str:
    """Return a display-only filename without path traversal components."""
    if not filename:
        return "file"
    return Path(filename).name[:120]