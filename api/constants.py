"""Endpoints, roles, status enums. A renamed endpoint is a one-line diff."""
from __future__ import annotations


class UsersEndpoints:
    VERSION = "v2"
    BASE = f"/{VERSION}/users"        # GET (list) / POST
    DETAIL = BASE + "/{id}"           # GET / PUT / PATCH / DELETE -- .format(id=...)


class Roles:
    """Passed to TokenProvider.get_token(role=...) / ApiClient(role=...).
    Each maps to a required <API_ENV>_<ROLE>_TOKEN entry in .env (see
    .env.example) -- a role with no such entry is a ConfigError."""

    DEFAULT = "default"
    READ = "read"
    WRITE = "write"
    