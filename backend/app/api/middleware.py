"""One middleware: request id, access log line, and a safe 500 for unexpected errors."""

import logging
import re
import uuid
from collections.abc import Awaitable, Callable
from time import perf_counter

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.error_handlers import error_body
from app.logging_config import request_id_var

logger = logging.getLogger("app.request")

# Only accept a client-supplied id if it is short and plain, so it cannot pollute the logs
_SAFE_REQUEST_ID = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        supplied = request.headers.get("X-Request-ID", "")
        request_id = supplied if _SAFE_REQUEST_ID.match(supplied) else uuid.uuid4().hex[:12]
        token = request_id_var.set(request_id)
        started = perf_counter()
        try:
            try:
                response = await call_next(request)
            except Exception:
                logger.exception("unhandled error", extra={"path": request.url.path})
                response = JSONResponse(
                    status_code=500,
                    content=error_body(
                        "internal_error",
                        "Something went wrong on our side. "
                        f"Quote request id {request_id} if it persists.",
                    ),
                )
            response.headers["X-Request-ID"] = request_id
            logger.info(
                "request",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "duration_ms": round((perf_counter() - started) * 1000, 1),
                },
            )
            return response
        finally:
            request_id_var.reset(token)
