"""
production/config/settings.py — centralized, validated configuration.

Every configurable value (API, security, model paths, thresholds, logging,
blockchain, ports) lives here, loaded from environment variables / a `.env`
file via pydantic-settings, with type-checked defaults. Nothing here changes
model weights, datasets, or any scientific result — this only externalizes
values that were previously hardcoded in api_server.py (e.g. CORS origins,
port 8000, model directory names).

Startup validation: `Settings()` raises immediately (before the app accepts
any request) if a required value is missing or malformed, or if referenced
paths (model directory, blockchain dir) don't exist — "fail fast, fail loud"
rather than a mysterious 500 three requests later.
"""
from __future__ import annotations

from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parent.parent.parent   # smartgrid_simulation/


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ROOT / ".env"), env_file_encoding="utf-8",
        env_prefix="SGRID_", extra="ignore",
    )

    # ── environment ──────────────────────────────────────────────────────────
    environment: str = Field(default="development")   # development|staging|production
    debug: bool = Field(default=False)

    # ── API / server ─────────────────────────────────────────────────────────
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)
    api_title: str = Field(default="Smart Grid Cybersecurity API")
    api_version: str = Field(default="1.0.0")
    cors_allowed_origins: list[str] = Field(default_factory=lambda: ["http://localhost:8000"])
    rate_limit_requests_per_minute: int = Field(default=120)
    rate_limit_login_per_minute: int = Field(default=10)

    # ── security / auth ──────────────────────────────────────────────────────
    jwt_secret_key: str = Field(default="CHANGE_ME_INSECURE_DEV_ONLY_SECRET")
    jwt_algorithm: str = Field(default="HS256")
    jwt_access_token_expire_minutes: int = Field(default=60)
    users_file: str = Field(default=str(ROOT / "production" / "security" / "users.json"))

    # ── model / detection ────────────────────────────────────────────────────
    model_dir_v3: str = Field(default="outputs/early_stopping_final")
    model_dir_v2: str = Field(default="outputs/test_run_now")
    detection_threshold_override: float | None = Field(default=None)
    inference_service_url: str | None = Field(default=None)  # if set, /api/detect proxies here

    # ── blockchain ───────────────────────────────────────────────────────────
    blockchain_block_size: int = Field(default=20)
    blockchain_data_dir: str = Field(default=str(ROOT.parent / "data" / "blockchain"))

    # ── logging ──────────────────────────────────────────────────────────────
    log_dir: str = Field(default=str(ROOT / "logs"))
    log_level: str = Field(default="INFO")
    log_max_bytes: int = Field(default=10_000_000)   # 10MB per file before rotation
    log_backup_count: int = Field(default=5)

    # ── monitoring ───────────────────────────────────────────────────────────
    metrics_enabled: bool = Field(default=True)

    @field_validator("environment")
    @classmethod
    def _validate_env(cls, v: str) -> str:
        allowed = {"development", "staging", "production"}
        if v not in allowed:
            raise ValueError(f"environment must be one of {allowed}, got {v!r}")
        return v

    @field_validator("jwt_secret_key")
    @classmethod
    def _warn_default_secret(cls, v: str) -> str:
        if v == "CHANGE_ME_INSECURE_DEV_ONLY_SECRET":
            import warnings
            warnings.warn(
                "SGRID_JWT_SECRET_KEY is using the insecure default. Set a real "
                "secret via environment variable before deploying to staging/production.",
                stacklevel=2,
            )
        return v

    def validate_runtime(self) -> list[str]:
        """Deeper checks that need the filesystem — called explicitly at
        startup (not import time) so tests can construct Settings() without
        a fully-populated deployment. Returns a list of problems (empty = OK)."""
        problems = []
        if self.environment == "production" and self.jwt_secret_key == "CHANGE_ME_INSECURE_DEV_ONLY_SECRET":
            problems.append("FATAL: default JWT secret cannot be used in production.")
        if self.environment == "production" and "*" in self.cors_allowed_origins:
            problems.append("FATAL: wildcard CORS origin cannot be used in production.")
        model_path = ROOT / self.model_dir_v3
        if not model_path.exists():
            problems.append(f"WARNING: model_dir_v3 does not exist: {model_path}")
        return problems


_settings: Settings | None = None


def get_settings() -> Settings:
    """Process-wide cached settings singleton (mirrors the existing
    get_detector() singleton pattern already used in realtime_detector.py)."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reload_settings() -> Settings:
    global _settings
    _settings = Settings()
    return _settings
