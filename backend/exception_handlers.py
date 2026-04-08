"""Register FastAPI handlers that emit the Phase 13 error envelope."""
from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.api_errors import (
    INFERENCE_BACKEND_UNAVAILABLE,
    KNOWLEDGE_NOT_FOUND,
    build_error_body,
    default_code_for_http_status,
)
from backend.services.exceptions import InferenceBackendUnavailable
from backend.services.exceptions import KnowledgeDocumentNotFound
from backend.services.exceptions import KnowledgeFeatureNotImplemented
from goat_ai.request_context import get_request_id

logger = logging.getLogger(__name__)

_REQUEST_ID_HEADER = "X-Request-ID"


def _attach_request_id(response: JSONResponse) -> JSONResponse:
    rid = get_request_id()
    if rid:
        response.headers[_REQUEST_ID_HEADER] = rid
    return response


def register_exception_handlers(app: FastAPI) -> None:
    """Attach handlers for domain and HTTP errors (call once on the app instance)."""

    @app.exception_handler(InferenceBackendUnavailable)
    def _inference_unavailable(_request: Request, _exc: InferenceBackendUnavailable) -> JSONResponse:
        return _attach_request_id(
            JSONResponse(
                status_code=503,
                content=build_error_body(
                    detail="AI backend unavailable",
                    code=INFERENCE_BACKEND_UNAVAILABLE,
                    status_code=503,
                ),
            ),
        )

    @app.exception_handler(KnowledgeFeatureNotImplemented)
    def _knowledge_not_implemented(_request: Request, exc: KnowledgeFeatureNotImplemented) -> JSONResponse:
        return _attach_request_id(
            JSONResponse(
                status_code=501,
                content=build_error_body(
                    detail=str(exc),
                    status_code=501,
                ),
            ),
        )

    @app.exception_handler(KnowledgeDocumentNotFound)
    def _knowledge_not_found(_request: Request, exc: KnowledgeDocumentNotFound) -> JSONResponse:
        return _attach_request_id(
            JSONResponse(
                status_code=404,
                content=build_error_body(
                    detail=str(exc),
                    code=KNOWLEDGE_NOT_FOUND,
                    status_code=404,
                ),
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    def _http_exception(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
        detail: str | list[Any] | dict[str, Any] = exc.detail  # type: ignore[assignment]
        code = default_code_for_http_status(exc.status_code)
        if isinstance(detail, str):
            content = build_error_body(detail=detail, code=code, status_code=exc.status_code)
        else:
            content = build_error_body(detail=detail, code=code, status_code=exc.status_code)
        return _attach_request_id(JSONResponse(status_code=exc.status_code, content=content))

    @app.exception_handler(RequestValidationError)
    def _validation_error(_request: Request, exc: RequestValidationError) -> JSONResponse:
        code = default_code_for_http_status(422)
        content = build_error_body(
            detail=jsonable_encoder(exc.errors()),
            code=code,
            status_code=422,
        )
        return _attach_request_id(JSONResponse(status_code=422, content=content))

    @app.exception_handler(Exception)
    def _unhandled_exception(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error on %s", request.url.path)
        code = default_code_for_http_status(500)
        content = build_error_body(detail="Internal server error", code=code, status_code=500)
        return _attach_request_id(JSONResponse(status_code=500, content=content))
