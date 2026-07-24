"""Global exception handlers — consistent error responses."""

from __future__ import annotations

from fastapi import Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from loguru import logger


async def integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
    logger.warning(f"Integrity error on {request.url.path}: {exc}")
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": "A record with that unique value already exists."},
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error(f"Unhandled error on {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal error occurred. Please try again later."},
    )
