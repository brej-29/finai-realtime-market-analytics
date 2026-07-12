from __future__ import annotations

from http import HTTPStatus
from typing import Any, Dict, Optional, Type

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import get_logger


class ErrorResponse(BaseModel):
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None


class AppError(Exception):
    """Base class for application-level errors."""

    code = "app_error"
    status_code = HTTPStatus.INTERNAL_SERVER_ERROR

    def __init__(self, message: str, *, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def to_response(self) -> ErrorResponse:
        return ErrorResponse(code=self.code, message=self.message, details=self.details)


class ProviderError(AppError):
    code = "provider_error"
    status_code = HTTPStatus.BAD_GATEWAY


class RateLimitExceededError(AppError):
    code = "rate_limit_exceeded"
    status_code = HTTPStatus.TOO_MANY_REQUESTS


class NotFoundError(AppError):
    code = "not_found"
    status_code = HTTPStatus.NOT_FOUND


class BadRequestError(AppError):
    code = "bad_request"
    status_code = HTTPStatus.BAD_REQUEST


class ResearchDisabledError(AppError):
    code = "research_disabled"
    status_code = HTTPStatus.SERVICE_UNAVAILABLE


class ResearchLimitError(AppError):
    code = "research_daily_limit"
    status_code = HTTPStatus.TOO_MANY_REQUESTS


def _app_error_handler(error_cls: Type[AppError]):
    async def handler(request: Request, exc: AppError) -> JSONResponse:  # type: ignore[type-arg]
        logger = get_logger("app.errors")
        logger.warning(
            "App error",
            extra={
                "code": exc.code,
                "path": request.url.path,
                "details": exc.details,
            },
        )
        error_payload = exc.to_response()
        return JSONResponse(
            status_code=error_cls.status_code,
            content=error_payload.model_dump(),
        )

    return handler


async def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    logger = get_logger("app.errors.http")
    logger.warning(
        "HTTP exception",
        extra={
            "status_code": exc.status_code,
            "path": request.url.path,
        },
    )
    payload = ErrorResponse(
        code="http_error",
        message=exc.detail if isinstance(exc.detail, str) else "HTTP error",
    )
    return JSONResponse(status_code=exc.status_code, content=payload.model_dump())


async def validation_exception_handler(request: Request, exc: ValidationError) -> JSONResponse:
    logger = get_logger("app.errors.validation")
    logger.warning(
        "Validation error",
        extra={"path": request.url.path},
    )
    payload = ErrorResponse(
        code="validation_error",
        message="Request validation failed",
        details={"errors": exc.errors()},
    )
    return JSONResponse(status_code=HTTPStatus.UNPROCESSABLE_ENTITY, content=payload.model_dump())


def register_exception_handlers(app: FastAPI) -> None:
    """Register global exception handlers on the FastAPI app."""
    app.add_exception_handler(ProviderError, _app_error_handler(ProviderError))
    app.add_exception_handler(RateLimitExceededError, _app_error_handler(RateLimitExceededError))
    app.add_exception_handler(NotFoundError, _app_error_handler(NotFoundError))
    app.add_exception_handler(BadRequestError, _app_error_handler(BadRequestError))
    app.add_exception_handler(ResearchDisabledError, _app_error_handler(ResearchDisabledError))
    app.add_exception_handler(ResearchLimitError, _app_error_handler(ResearchLimitError))
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(ValidationError, validation_exception_handler)  # type: ignore[arg-type]