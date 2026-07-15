"""Unit tests: request-ID correlation, rate limiting, structured error responses."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from production.middleware import RequestIdMiddleware, RateLimitMiddleware, register_exception_handlers


def _app():
    app = FastAPI()
    register_exception_handlers(app)
    app.add_middleware(RequestIdMiddleware)

    @app.get("/ok")
    def ok(): return {"ok": True}

    @app.get("/boom")
    def boom(): raise HTTPException(status_code=418, detail="teapot")

    @app.get("/crash")
    def crash(): raise ValueError("unexpected")

    return app


def test_request_id_header_present():
    client = TestClient(_app())
    r = client.get("/ok")
    assert "x-request-id" in r.headers
    assert len(r.headers["x-request-id"]) == 12


def test_response_time_header_present():
    client = TestClient(_app())
    r = client.get("/ok")
    assert "x-response-time-ms" in r.headers
    assert float(r.headers["x-response-time-ms"]) >= 0


def test_different_requests_get_different_ids():
    client = TestClient(_app())
    a = client.get("/ok").headers["x-request-id"]
    b = client.get("/ok").headers["x-request-id"]
    assert a != b


def test_http_exception_has_consistent_shape():
    client = TestClient(_app())
    r = client.get("/boom")
    assert r.status_code == 418
    body = r.json()
    assert body["error"] == "http_error"
    assert body["detail"] == "teapot"
    assert "request_id" in body


def test_unhandled_exception_returns_500_not_crash():
    client = TestClient(_app(), raise_server_exceptions=False)
    r = client.get("/crash")
    assert r.status_code == 500
    body = r.json()
    assert body["error"] == "internal_error"
    assert "request_id" in body


def test_rate_limit_blocks_after_threshold():
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware, requests_per_minute=3)

    @app.get("/x")
    def x(): return {"ok": True}

    client = TestClient(app)
    codes = [client.get("/x").status_code for _ in range(5)]
    assert codes[:3] == [200, 200, 200]
    assert codes[3:] == [429, 429]


def test_login_endpoint_has_stricter_rate_limit():
    """Login must be throttled far below the general API limit — a real
    brute-force mitigation, not just the generic per-IP budget."""
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware, requests_per_minute=120, login_requests_per_minute=3)

    @app.post("/api/auth/login")
    def login(): return {"ok": True}

    @app.get("/other")
    def other(): return {"ok": True}

    client = TestClient(app)
    login_codes = [client.post("/api/auth/login").status_code for _ in range(5)]
    assert login_codes == [200, 200, 200, 429, 429]
    # the general limit (120/min) must be unaffected by login's separate budget
    other_codes = [client.get("/other").status_code for _ in range(5)]
    assert other_codes == [200] * 5


def test_rate_limit_exempts_health_and_metrics():
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware, requests_per_minute=1)

    @app.get("/health")
    def health(): return {"status": "alive"}

    client = TestClient(app)
    codes = [client.get("/health").status_code for _ in range(5)]
    assert codes == [200] * 5   # never rate-limited
