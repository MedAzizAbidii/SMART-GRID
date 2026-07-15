"""
production/middleware.py — request-ID correlation, rate limiting, and
consistent structured error responses for every endpoint (REST hardening).
"""
from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from production.logging.setup import new_request_id, request_id_var


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Every request gets a short correlation ID, echoed in the response
    header and available to every log call made while handling it (via the
    request_id_var contextvar) — the thread that ties the five separated log
    files back together for one incident."""

    async def dispatch(self, request: Request, call_next):
        rid = new_request_id()
        t0 = time.perf_counter()
        response = await call_next(request)
        response.headers["X-Request-ID"] = rid
        response.headers["X-Response-Time-ms"] = f"{(time.perf_counter() - t0) * 1000:.2f}"
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory sliding-window rate limiter, per client IP. Adequate
    for a single-process deployment; a multi-worker/multi-node deployment
    should move this to a shared store (Redis) — documented in the deployment
    guide, not silently pretended away.

    Login gets its OWN, much stricter limit (default 10/min vs 120/min for
    everything else): a general-purpose API limit is deliberately generous
    for legitimate polling traffic, which is far too permissive for a
    password-guessing endpoint — brute force needs its own budget, not a
    side effect of the general one."""

    def __init__(self, app, requests_per_minute: int = 120, login_requests_per_minute: int = 10,
                login_path: str = "/api/auth/login"):
        super().__init__(app)
        self.limit = requests_per_minute
        self.login_limit = login_requests_per_minute
        self.login_path = login_path
        self._hits: dict[str, deque] = defaultdict(deque)
        self._login_hits: dict[str, deque] = defaultdict(deque)

    @staticmethod
    def _check(window: deque, limit: int, now: float) -> bool:
        """Returns True if the request is allowed (and records it)."""
        while window and now - window[0] > 60:
            window.popleft()
        if len(window) >= limit:
            return False
        window.append(now)
        return True

    async def dispatch(self, request: Request, call_next):
        if request.url.path in ("/health", "/metrics"):
            return await call_next(request)   # never rate-limit health/monitoring probes
        client = request.client.host if request.client else "unknown"
        now = time.time()

        if request.url.path == self.login_path:
            if not self._check(self._login_hits[client], self.login_limit, now):
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={"error": "rate_limited",
                            "detail": f"Max {self.login_limit} login attempts/minute exceeded",
                            "request_id": request_id_var.get()},
                )
            return await call_next(request)

        if not self._check(self._hits[client], self.limit, now):
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"error": "rate_limited", "detail": f"Max {self.limit} requests/minute exceeded",
                        "request_id": request_id_var.get()},
            )
        return await call_next(request)


def register_exception_handlers(app: FastAPI) -> None:
    """Consistent {error, detail, request_id} JSON shape for every failure
    mode, instead of FastAPI's default (inconsistent across validation vs
    HTTP vs unhandled exceptions)."""

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"error": "validation_error", "detail": exc.errors(),
                    "request_id": request_id_var.get()},
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": "http_error", "detail": exc.detail,
                    "request_id": request_id_var.get()},
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        import logging
        logging.getLogger("smartgrid.system").exception(
            "Unhandled exception", extra={"extra_fields": {"path": str(request.url)}})
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "internal_error", "detail": "An unexpected error occurred",
                    "request_id": request_id_var.get()},
        )
