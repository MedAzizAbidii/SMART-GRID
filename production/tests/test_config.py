"""Unit tests: configuration loading + startup validation."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from production.config.settings import Settings


def test_settings_load_with_defaults():
    s = Settings()
    assert s.environment in ("development", "staging", "production")
    assert s.api_port == 8000


def test_settings_rejects_invalid_environment():
    try:
        Settings(environment="not_a_real_env")
        assert False, "should have raised"
    except Exception:
        pass


def test_validate_runtime_flags_default_secret_in_production():
    s = Settings(environment="production", jwt_secret_key="CHANGE_ME_INSECURE_DEV_ONLY_SECRET")
    problems = s.validate_runtime()
    assert any("JWT secret" in p for p in problems)


def test_validate_runtime_flags_wildcard_cors_in_production():
    s = Settings(environment="production", jwt_secret_key="a-real-secret-value",
                cors_allowed_origins=["*"])
    problems = s.validate_runtime()
    assert any("CORS" in p for p in problems)


def test_validate_runtime_clean_in_development():
    s = Settings(environment="development")
    problems = s.validate_runtime()
    assert not any("FATAL" in p for p in problems)


def test_settings_singleton_cache():
    from production.config.settings import get_settings, reload_settings
    a = get_settings(); b = get_settings()
    assert a is b
    c = reload_settings()
    assert c is not a
