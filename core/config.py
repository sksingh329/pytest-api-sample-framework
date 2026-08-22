"""Parses the framework's pytest.ini section (plus environments.py +
env-var overrides) into a frozen Settings dataclass. Validates and fails
fast at collection time with readable messages -- nothing here talks HTTP.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from core.errors import ConfigError

_VALID_LOG_LEVELS = ("ERROR", "WARNING", "INFO", "DEBUG", "TRACE")

# ini key -> env var name used to override it in CI, regardless of api_env.
_ENV_VAR_OVERRIDES = {
    "api_env": "API_ENV",
    "api_log_level": "API_LOG_LEVEL",
    "api_timeout": "API_TIMEOUT",
    "api_retries": "API_RETRIES",
    "api_report_dir": "API_REPORT_DIR",
    "api_redact_keys": "API_REDACT_KEYS",
    "api_max_body_chars": "API_MAX_BODY_CHARS",
    "api_latency_budget_ms": "API_LATENCY_BUDGET_MS",
    "api_schema_dir": "API_SCHEMA_DIR",
}

# environments.ENVIRONMENTS[api_env] key -> env var override (applies to
# whichever environment is active -- handy for CI, which already knows
# its target)
_ENV_BLOCK_OVERRIDES = {
    "BASE_URL": "API_BASE_URL",
}


@dataclass(frozen=True)
class Settings:
    """Immutable, fully-resolved framework configuration for one test run."""

    api_env: str
    api_log_level: str
    api_timeout: float
    api_retries: int
    api_report_dir: Path
    api_redact_keys: tuple[str, ...]
    api_max_body_chars: int
    api_latency_budget_ms: int
    api_schema_dir: Path

    # resolved from environments.ENVIRONMENTS[api_env]
    base_url: str

    def masked(self) -> dict:
        """Safe-to-log view (no credentials, no full urls beyond host)."""
        return {
            "api_env": self.api_env,
            "base_url": self.base_url,
            "log_level": self.api_log_level,
            "timeout": self.api_timeout,
            "retries": self.api_retries,
        }


def _load_env_block(api_env: str) -> dict:
    """environments.ENVIRONMENTS[api_env] -- see environments.py for the
    full set of keys and a worked example (all environments in one file)."""
    from environments import ENVIRONMENTS

    try:
        return ENVIRONMENTS[api_env]
    except KeyError as exc:
        raise ConfigError(
            f"no environments.ENVIRONMENTS[{api_env!r}] found for api_env={api_env!r}. "
            f"Available environments: {sorted(ENVIRONMENTS) or 'none'}."
        ) from exc


def _getini_str(pytest_config, key: str, default: str) -> str:
    env_var = _ENV_VAR_OVERRIDES.get(key)
    if env_var and os.environ.get(env_var):
        return os.environ[env_var]
    try:
        value = pytest_config.getini(key)
    except (KeyError, ValueError):
        value = None
    return value if value else default


def load_settings(pytest_config) -> Settings:
    """Build a validated, frozen Settings from a pytest Config object.

    Raises ConfigError (fail fast, readable message) on anything malformed
    so collection stops before a single request is sent.
    """
    api_env = _getini_str(pytest_config, "api_env", "dev").strip()
    log_level = _getini_str(pytest_config, "api_log_level", "INFO").strip().upper()
    if log_level not in _VALID_LOG_LEVELS:
        raise ConfigError(
            f"api_log_level={log_level!r} is invalid; must be one of {_VALID_LOG_LEVELS}"
        )

    def _int(key: str, default: str) -> int:
        raw = _getini_str(pytest_config, key, default)
        try:
            return int(raw)
        except ValueError as exc:
            raise ConfigError(f"{key}={raw!r} is not an integer") from exc

    def _float(key: str, default: str) -> float:
        raw = _getini_str(pytest_config, key, default)
        try:
            return float(raw)
        except ValueError as exc:
            raise ConfigError(f"{key}={raw!r} is not a number") from exc

    timeout = _float("api_timeout", "30")
    retries = _int("api_retries", "2")
    report_dir = Path(_getini_str(pytest_config, "api_report_dir", "reports/"))
    redact_raw = _getini_str(pytest_config, "api_redact_keys", "authorization, password, token")
    redact_keys = tuple(k.strip().lower() for k in redact_raw.split(",") if k.strip())
    max_body_chars = _int("api_max_body_chars", "4000")
    latency_budget_ms = _int("api_latency_budget_ms", "800")
    schema_dir = Path(_getini_str(pytest_config, "api_schema_dir", "api/schemas"))

    if timeout <= 0:
        raise ConfigError(f"api_timeout must be > 0, got {timeout}")
    if retries < 0:
        raise ConfigError(f"api_retries must be >= 0, got {retries}")
    if max_body_chars <= 0:
        raise ConfigError(f"api_max_body_chars must be > 0, got {max_body_chars}")

    env_block = _load_env_block(api_env)

    def _env_value(attr: str, required: bool = True) -> str | None:
        override_var = _ENV_BLOCK_OVERRIDES.get(attr)
        if override_var and os.environ.get(override_var):
            return os.environ[override_var]
        value = env_block.get(attr)
        if required and not value:
            raise ConfigError(
                f"environments.ENVIRONMENTS[{api_env!r}] is missing required {attr} "
                f"(or set env var {override_var})"
            )
        return value

    base_url = _env_value("BASE_URL").rstrip("/")

    return Settings(
        api_env=api_env,
        api_log_level=log_level,
        api_timeout=timeout,
        api_retries=retries,
        api_report_dir=report_dir,
        api_redact_keys=redact_keys,
        api_max_body_chars=max_body_chars,
        api_latency_budget_ms=latency_budget_ms,
        api_schema_dir=schema_dir,
        base_url=base_url,
    )
