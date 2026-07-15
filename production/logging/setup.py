"""
production/logging/setup.py — structured JSON logging, separated by concern.

Five independent loggers, each its own rotating file (bounded size — directly
answers the Phase-3 finding that unbounded log/ledger growth is a reliability
risk):
  app.log         — general application lifecycle
  predictions.log — every model prediction (score, threshold, decision)
  attacks.log     — confirmed anomaly/attack detections only
  blockchain.log  — ledger writes, block seals, validation
  system.log      — errors, exceptions, startup/shutdown, config problems

Every record includes a timestamp, logger name, level, and (via contextvars)
the current request_id, so a single incident can be traced across all five
files without a bespoke correlation system.
"""
from __future__ import annotations

import contextvars
import json
import logging
import logging.handlers
import sys
import uuid
from pathlib import Path

request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "request_id": getattr(record, "request_id", "-"),
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        extra = getattr(record, "extra_fields", None)
        if extra:
            payload.update(extra)
        return json.dumps(payload, default=str)


LOGGERS = {
    "app": "app.log",
    "predictions": "predictions.log",
    "attacks": "attacks.log",
    "blockchain": "blockchain.log",
    "system": "system.log",
}

_configured = False


def setup_logging(log_dir: str, level: str = "INFO", max_bytes: int = 10_000_000,
                  backup_count: int = 5) -> dict[str, logging.Logger]:
    global _configured
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    fmt = JsonFormatter()
    req_filter = RequestIdFilter()
    loggers = {}
    for name, filename in LOGGERS.items():
        logger = logging.getLogger(f"smartgrid.{name}")
        logger.setLevel(getattr(logging, level.upper(), logging.INFO))
        logger.propagate = False
        if not _configured:
            handler = logging.handlers.RotatingFileHandler(
                Path(log_dir) / filename, maxBytes=max_bytes, backupCount=backup_count,
                encoding="utf-8")
            handler.setFormatter(fmt)
            handler.addFilter(req_filter)
            logger.addHandler(handler)
            # also echo 'system' and 'app' to stderr for container log collection
            if name in ("app", "system"):
                stream = logging.StreamHandler(sys.stderr)
                stream.setFormatter(fmt)
                stream.addFilter(req_filter)
                logger.addHandler(stream)
        loggers[name] = logger
    _configured = True
    return loggers


def new_request_id() -> str:
    rid = uuid.uuid4().hex[:12]
    request_id_var.set(rid)
    return rid


def log_extra(**fields) -> dict:
    """Attach structured fields to a log call: logger.info("msg", extra=log_extra(x=1))."""
    return {"extra_fields": fields}
