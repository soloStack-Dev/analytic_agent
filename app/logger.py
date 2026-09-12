from __future__ import annotations

import logging

from .config import LOGS_DIR


def setup_logging() -> logging.Logger:
    """Create the shared console, application, and error log handlers once."""
    logger = logging.getLogger("chart_agent")
    if logger.handlers:
        # Uvicorn reloads can import this module more than once; avoid duplicate lines.
        return logger

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    logger.setLevel(logging.INFO)

    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(formatter)
    logger.addHandler(console)

    # Keep errors separate so production troubleshooting does not require filtering
    # a large general application log.
    error_file = logging.FileHandler(LOGS_DIR / "error.log", encoding="utf-8")
    error_file.setLevel(logging.ERROR)
    error_file.setFormatter(formatter)
    logger.addHandler(error_file)

    all_file = logging.FileHandler(LOGS_DIR / "app.log", encoding="utf-8")
    all_file.setLevel(logging.INFO)
    all_file.setFormatter(formatter)
    logger.addHandler(all_file)

    return logger


logger = setup_logging()