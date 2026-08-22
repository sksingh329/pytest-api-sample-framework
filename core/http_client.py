"""ApiClient: a pooled, authenticated HTTP client returning a thin
ApiResponse wrapper (never a raw requests.Response) and emitting a
RequestRecord for every attempt -- including retries -- with timing.

Retries are implemented manually (not via urllib3's Retry adapter) so that
each attempt is individually observable: a test that succeeds on attempt
three must produce three distinct records, not one opaque final response.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Sequence

import requests
from requests.adapters import HTTPAdapter

from core.auth import DEFAULT_ROLE, TokenProvider
from core.config import Settings
from core.errors import TransportError

_RETRYABLE_STATUSES = frozenset({429, 502, 503, 504})
_DEFAULT_POOL_SIZE = 20


@dataclass
class RequestRecord:
    """One HTTP attempt -- retries produce one record each, in order."""

    request_id: str
    attempt: int
    max_attempts: int
    method: str
    url: str
    request_headers: dict
    request_body: Any
    status_code: int | None
    response_headers: dict
    response_body: Any
    duration_ms: float
    error: str | None
    retryable: bool
    started_at: float
    service: str | None = None


@dataclass
class ApiResponse:
    """Thin wrapper around the final (successful-enough-to-return) attempt.

    Tests and assertions interact only with this, never requests.Response.
    """

    status_code: int
    headers: Mapping[str, str]
    text: str
    url: str
    elapsed_ms: float
    request_id: str
    attempts: int
    # the body that was SENT, not received -- kept alongside the response
    # so a test can assert the API echoed it back correctly without a
    # separate wrapper object (e.g. assert_field(resp, "email",
    # resp.request_body["email"])), and it shows up in the report's
    # request panel too.
    request_body: Any = None
    _json_cache: Any = field(default=None, repr=False)
    _json_loaded: bool = field(default=False, repr=False)

    def json(self) -> Any:
        if not self._json_loaded:
            import json as _json

            try:
                self._json_cache = _json.loads(self.text) if self.text else None
            except ValueError:
                self._json_cache = None
            self._json_loaded = True
        return self._json_cache

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 400


class ApiClient:
    """Pooled session + retry policy + bearer auth injection, per service."""

    def __init__(
        self,
        settings: Settings,
        token_provider: TokenProvider,
        role: str = DEFAULT_ROLE,
        recorder: "Any | None" = None,
        default_headers: Mapping[str, str] | None = None,
    ):
        self._settings = settings
        self._token_provider = token_provider
        self._role = role
        self._recorder = recorder  # wired up in M2 (core.recorder.Recorder)
        self._default_headers = dict(default_headers or {})

        self._session = requests.Session()
        adapter = HTTPAdapter(pool_connections=_DEFAULT_POOL_SIZE, pool_maxsize=_DEFAULT_POOL_SIZE)
        self._session.mount("http://", adapter)
        self._session.mount("https://", adapter)

    def request(
        self,
        method: str,
        path: str,
        *,
        json: Any = None,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
        service: str | None = None,
    ) -> ApiResponse:
        url = f"{self._settings.base_url}{path}" if path.startswith("/") else path
        request_id = uuid.uuid4().hex[:12]
        max_attempts = self._settings.api_retries + 1

        merged_headers = dict(self._default_headers)
        merged_headers["Authorization"] = f"Bearer {self._token_provider.get_token(self._role)}"
        if headers:
            merged_headers.update(headers)

        last_exc: Exception | None = None
        for attempt in range(1, max_attempts + 1):
            started_at = time.time()
            t0 = time.perf_counter()
            try:
                resp = self._session.request(
                    method=method.upper(),
                    url=url,
                    json=json,
                    params=params,
                    headers=merged_headers,
                    timeout=self._settings.api_timeout,
                )
                duration_ms = (time.perf_counter() - t0) * 1000
                retryable = resp.status_code in _RETRYABLE_STATUSES
                record = RequestRecord(
                    request_id=request_id,
                    attempt=attempt,
                    max_attempts=max_attempts,
                    method=method.upper(),
                    url=url,
                    request_headers=merged_headers,
                    request_body=json,
                    status_code=resp.status_code,
                    response_headers=dict(resp.headers),
                    response_body=_safe_body(resp),
                    duration_ms=duration_ms,
                    error=None,
                    retryable=retryable,
                    started_at=started_at,
                    service=service,
                )
                self._emit(record)

                if retryable and attempt < max_attempts:
                    time.sleep(_backoff_seconds(attempt))
                    continue

                return ApiResponse(
                    status_code=resp.status_code,
                    headers=dict(resp.headers),
                    text=resp.text,
                    url=url,
                    elapsed_ms=duration_ms,
                    request_id=request_id,
                    attempts=attempt,
                    request_body=json,
                )
            except requests.RequestException as exc:
                duration_ms = (time.perf_counter() - t0) * 1000
                last_exc = exc
                record = RequestRecord(
                    request_id=request_id,
                    attempt=attempt,
                    max_attempts=max_attempts,
                    method=method.upper(),
                    url=url,
                    request_headers=merged_headers,
                    request_body=json,
                    status_code=None,
                    response_headers={},
                    response_body=None,
                    duration_ms=duration_ms,
                    error=str(exc),
                    retryable=True,
                    started_at=started_at,
                    service=service,
                )
                self._emit(record)
                if attempt < max_attempts:
                    time.sleep(_backoff_seconds(attempt))
                    continue

        raise TransportError(
            f"{method.upper()} {url} failed after {max_attempts} attempt(s): {last_exc}"
        )

    def get(self, path: str, **kw) -> ApiResponse:
        return self.request("GET", path, **kw)

    def post(self, path: str, **kw) -> ApiResponse:
        return self.request("POST", path, **kw)

    def put(self, path: str, **kw) -> ApiResponse:
        return self.request("PUT", path, **kw)

    def patch(self, path: str, **kw) -> ApiResponse:
        return self.request("PATCH", path, **kw)

    def delete(self, path: str, **kw) -> ApiResponse:
        return self.request("DELETE", path, **kw)

    def _emit(self, record: RequestRecord) -> None:
        if self._recorder is not None:
            self._recorder.record_request(record)


def _safe_body(resp: requests.Response) -> Any:
    try:
        return resp.json()
    except ValueError:
        return resp.text


def _backoff_seconds(attempt: int) -> float:
    return min(0.25 * (2 ** (attempt - 1)), 2.0)
