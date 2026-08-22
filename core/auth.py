"""TokenProvider: resolves a fixed bearer token per role/tenant.

API test suites authenticate with a fixed bearer token, not a login flow --
so there is nothing to acquire, cache-with-expiry, or refresh. A token is
read once (per role) from os.environ, by the convention
<API_ENV>_<ROLE>_TOKEN -- e.g. role="read" in the "dev" environment reads
DEV_READ_TOKEN -- and held in memory for the rest of the session. Populate
those variables via a .env file (gitignored -- see .env.example), loaded
into os.environ by the root conftest.py before anything else runs, or via
real environment variables in CI.
"""
from __future__ import annotations

import os
import threading

from core.config import Settings
from core.errors import ConfigError

DEFAULT_ROLE = "default"


def mask_token(token: str) -> str:
    """Masked fingerprint for logs: first 4 + last 4 chars only."""
    if not token:
        return "<empty>"
    if len(token) <= 10:
        return "*" * len(token)
    return f"{token[:4]}...{token[-4:]}"


class TokenProvider:
    """Resolves and caches a fixed bearer token per role/tenant.

    In-process callers share an in-memory cache guarded by a thread lock --
    that's the whole story; there's no HTTP call, no expiry, and (since
    reading an already-set env var is cheap and side-effect-free) no
    cross-process coordination needed for xdist workers either.
    """

    def __init__(self, settings: Settings):
        self._settings = settings
        self._lock = threading.Lock()
        self._cache: dict[str, str] = {}

    def get_token(self, role: str = DEFAULT_ROLE) -> str:
        with self._lock:
            cached = self._cache.get(role)
        if cached is not None:
            return cached

        env_var = f"{self._settings.api_env.upper()}_{role.upper()}_TOKEN"
        token = os.environ.get(env_var)
        if not token:
            raise ConfigError(
                f"no bearer token for role={role!r} in environment={self._settings.api_env!r}: "
                f"set {env_var} in .env (see .env.example) or as a real env var in CI"
            )

        with self._lock:
            self._cache[role] = token
        return token

    def fingerprint(self, role: str = DEFAULT_ROLE) -> str:
        with self._lock:
            cached = self._cache.get(role)
        return mask_token(cached) if cached is not None else "<not resolved>"
