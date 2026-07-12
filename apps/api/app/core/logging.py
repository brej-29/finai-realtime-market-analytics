from __future__ import annotations

import logging
import sys
import time
import uuid
from typing import Any, Callable

from fastapi import FastAPI, Request, Response

from app.core.config import get_settings


class _RequestIdDefaultFilter(logging.Filter):
    """Default request_id for records from libraries that don't set it.

    Without this, any log record emitted by third-party code (uvicorn,
    apscheduler, httpx, ...) crashes the formatter with KeyError: 'request_id'.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):
            record.request_id = "-"
        return True


def configure_logging() -> None:
    """Configure root logging for the application.

    Uses a simple JSON-style log format that is friendly for hosted platforms.
    """
    settings = get_settings()
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        fmt=(
            '{"ts":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s",'
            '"message":"%(message)s","request_id":"%(request_id)s"}'
        ),
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )
    handler.setFormatter(formatter)
    handler.addFilter(_RequestIdDefaultFilter())

    root = logging.getLogger()
    root.setLevel(log_level)
    # Avoid duplicate handlers if configure_logging is called multiple times
    if not root.handlers:
        root.addHandler(handler)


def get_logger(name: str | None = None) -> logging.LoggerAdapter:
    """Return a logger adapter that always has a request_id field.

    When no request_id is available, it defaults to "-".
    """
    logger = logging.getLogger(name)
    return logging.LoggerAdapter(logger, extra={"request_id": "-"})  # type: ignore[arg-type]


async def logging_middleware(request: Request, call_next: Callable[[Request], Any]) -> Response:
    """Middleware that logs each request with a request_id and latency."""
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id

    logger = logging.LoggerAdapter(
        logging.getLogger("app.request"),
        extra={"request_id": request_id},
    )

    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        # Let exception handlers manage the response, but log here as well.
        logger.exception(
            "Unhandled exception during request",
            extra={
                "path": request.url.path,
                "method": request.method,
            },
        )
        raise
    duration_ms = (time.perf_counter() - start) * 1000.0

    logger.info(
        "request completed",
        extra={
            "path": request.url.path,
            "method": request.method,
            "status_code": response.status_code,
            "duration_ms": round(duration_ms, 2),
        },
    )

    # Expose request id to clients (helpful for debugging)
    response.headers["X-Request-ID"] = request_id
    return response


def setup_app_logging(app: FastAPI) -> None:
    """Attach logging middleware to the FastAPI app."""
    configure_logging()
    app.middleware("http")(logging_middleware)