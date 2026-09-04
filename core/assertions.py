"""The only public verification surface. Log first, raise second: every
check builds an AssertionRecord, hands it to whichever Recorder is active
for the current test (pass or fail), and only then raises. A bare `assert`
in a test produces no record and simply vanishes from the report -- that's
why tests must go through here instead.
"""
from __future__ import annotations

import contextvars
import re
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Mapping

from core.errors import VerificationError
from core.http_client import ApiResponse

_PATH_TOKEN = re.compile(r"[^.\[\]]+|\[\d+\]")

# None outside soft_assertions(); a list while inside one, collecting
# messages for the single aggregated raise at block exit.
_soft_failures: "contextvars.ContextVar[list[str] | None]" = contextvars.ContextVar("soft_failures", default=None)

_MISSING = object()


@dataclass
class AssertionRecord:
    name: str
    passed: bool
    expected: Any
    actual: Any
    kind: str
    violations: list[dict] | None = None


def _emit(record: AssertionRecord) -> None:
    from core.recorder import get_active_recorder  # deferred: avoid import cycle

    recorder = get_active_recorder()
    if recorder is not None:
        recorder.record_assertion(record)


def _verify(record: AssertionRecord, message: str) -> None:
    _emit(record)
    if record.passed:
        return
    failures = _soft_failures.get()
    if failures is not None:
        failures.append(message)
    else:
        raise VerificationError(message)


@contextmanager
def soft_assertions():
    """Collects every failure raised inside the block (each still logged
    individually as it happens), then raises ONE aggregated VerificationError
    at exit if any failed -- instead of stopping at the first one."""
    token = _soft_failures.set([])
    try:
        yield
    finally:
        failures = _soft_failures.get()
        _soft_failures.reset(token)
        if failures:
            bullet_list = "\n".join(f"  - {f}" for f in failures)
            raise VerificationError(f"{len(failures)} check(s) failed in soft_assertions():\n{bullet_list}")


def _get_path(data: Any, path: str) -> Any:
    """Resolve a dotted/indexed path, e.g. 'items[0].id' or 'user.email'."""
    current = data
    for token in _PATH_TOKEN.findall(path):
        if token.startswith("["):
            current = current[int(token[1:-1])]
        else:
            current = current[token]
    return current


def _safe_get(body: Any, path: str) -> Any:
    try:
        return _get_path(body, path)
    except (KeyError, IndexError, TypeError):
        return _MISSING


def assert_status(resp: ApiResponse, expected: int | Iterable[int]) -> None:
    """Exact status code, or membership in a set of acceptable codes."""
    allowed = set(expected) if isinstance(expected, (set, list, tuple)) else {expected}
    passed = resp.status_code in allowed
    label = str(next(iter(allowed))) if len(allowed) == 1 else "one of " + str(sorted(allowed))
    record = AssertionRecord("assert_status", passed, label, str(resp.status_code), "status")
    _verify(record, f"expected status {label}, got {resp.status_code}")


def assert_field(resp: ApiResponse, path: str, value: Any) -> None:
    """Dotted/indexed path equality against the response body."""
    actual = _safe_get(resp.json(), path)
    passed = actual is not _MISSING and actual == value
    display_actual = "<missing>" if actual is _MISSING else actual
    record = AssertionRecord(f"assert_field({path})", passed, value, display_actual, "field")
    _verify(record, f"field {path!r}: expected {value!r}, got {display_actual!r}")


def assert_fields(resp: ApiResponse, mapping: Mapping[str, Any]) -> None:
    """One record per path (not one blob), one aggregated raise for the set."""
    body = resp.json()
    failures = []
    for path, value in mapping.items():
        actual = _safe_get(body, path)
        passed = actual is not _MISSING and actual == value
        display_actual = "<missing>" if actual is _MISSING else actual
        record = AssertionRecord(f"assert_field({path})", passed, value, display_actual, "field")
        _emit(record)
        if not passed:
            failures.append(f"field {path!r}: expected {value!r}, got {display_actual!r}")
    if failures:
        bullet_list = "\n".join(f"  - {f}" for f in failures)
        raise VerificationError(f"assert_fields: {len(failures)} field(s) mismatched:\n{bullet_list}")


def assert_field_present(resp: ApiResponse, path: str) -> None:
    """Existence + non-null -- for generated ids, timestamps, etc."""
    actual = _safe_get(resp.json(), path)
    passed = actual is not _MISSING and actual is not None
    display_actual = "<missing>" if actual is _MISSING else actual
    record = AssertionRecord(f"assert_field_present({path})", passed, "present & non-null", display_actual, "field")
    _verify(record, f"field {path!r} expected present & non-null, got {display_actual!r}")


def _find_header(headers: Mapping[str, str], name: str) -> str | None:
    # HTTP header names are case-insensitive; don't make a test's pass/fail
    # depend on the server's casing (e.g. "X-Pagination-Total" vs
    # "x-pagination-total").
    name_lower = name.lower()
    for key, value in headers.items():
        if key.lower() == name_lower:
            return value
    return None


def assert_header(resp: ApiResponse, name: str, value: str) -> None:
    """Case-insensitive header equality -- e.g. content-type, a pagination
    total, a rate-limit value."""
    actual = _find_header(resp.headers, name)
    passed = actual is not None and actual == value
    display_actual = "<missing>" if actual is None else actual
    record = AssertionRecord(f"assert_header({name})", passed, value, display_actual, "header")
    _verify(record, f"header {name!r}: expected {value!r}, got {display_actual!r}")


def assert_header_present(resp: ApiResponse, name: str) -> None:
    """Existence check -- e.g. a pagination header (X-Pagination-Total)
    whose exact value isn't worth pinning in the test."""
    actual = _find_header(resp.headers, name)
    passed = actual is not None
    display_actual = "<missing>" if actual is None else actual
    record = AssertionRecord(f"assert_header_present({name})", passed, "present", display_actual, "header")
    _verify(record, f"header {name!r} expected present, got {display_actual!r}")


def assert_schema(resp: ApiResponse, name: str) -> None:
    """Full contract validation against a registered pydantic model (see
    core.schemas.SchemaRegistry, indexed from api_schema_dir), flagging
    both missing required fields and unexpected extra ones (drift)."""
    from core.schemas import get_registry  # deferred: avoid import cycle

    problems = get_registry().validate(name, resp.json())
    passed = not problems
    record = AssertionRecord(
        f"assert_schema({name})",
        passed,
        "0 violations",
        "0 violations" if passed else f"{len(problems)} violation(s)",
        "schema",
        violations=problems or None,
    )
    if passed:
        _verify(record, "")
        return
    bullet_list = "\n".join(f"  - {p['path']}: {p['problem']}" for p in problems)
    _verify(record, f"schema {name!r}: {len(problems)} violation(s):\n{bullet_list}")


def assert_list(
    resp: ApiResponse,
    path: str,
    *,
    length: int | tuple[int, int] | None = None,
    unique_by: str | None = None,
    sorted_by: str | None = None,
    descending: bool = False,
    predicate: Callable[[Any], bool] | None = None,
    predicate_name: str = "predicate",
) -> None:
    """Length, uniqueness, sort order, and a per-item predicate -- each its
    own record, one aggregated raise for the set."""
    items = _safe_get(resp.json(), path)
    if items is _MISSING or not isinstance(items, list):
        record = AssertionRecord(f"assert_list({path})", False, "a list", "<missing or not a list>", "list")
        _verify(record, f"path {path!r} did not resolve to a list")
        return

    failures = []

    if length is not None:
        if isinstance(length, tuple):
            passed = length[0] <= len(items) <= length[1]
            expected_label = f"{length[0]}..{length[1]}"
        else:
            passed = len(items) == length
            expected_label = str(length)
        record = AssertionRecord(f"assert_list({path}, length)", passed, expected_label, str(len(items)), "list")
        _emit(record)
        if not passed:
            failures.append(f"length: expected {expected_label}, got {len(items)}")

    if unique_by is not None:
        keys = [_safe_get(i, unique_by) for i in items]
        passed = len(keys) == len(set(map(str, keys)))
        record = AssertionRecord(f"assert_list({path}, unique_by={unique_by})", passed, "unique", "duplicates found" if not passed else "unique", "list")
        _emit(record)
        if not passed:
            failures.append(f"unique_by {unique_by!r}: duplicate values found")

    if sorted_by is not None:
        keys = [_safe_get(i, sorted_by) for i in items]
        expected_order = sorted(keys, reverse=descending)
        passed = keys == expected_order
        record = AssertionRecord(
            f"assert_list({path}, sorted_by={sorted_by})", passed,
            "descending" if descending else "ascending",
            "descending" if descending else "ascending" if passed else "out of order",
            "list",
        )
        _emit(record)
        if not passed:
            failures.append(f"sorted_by {sorted_by!r}: not {'descending' if descending else 'ascending'}")

    if predicate is not None:
        bad = [i for i in items if not predicate(i)]
        passed = not bad
        record = AssertionRecord(f"assert_list({path}, {predicate_name})", passed, "all items match", f"{len(bad)} item(s) failed", "list")
        _emit(record)
        if not passed:
            failures.append(f"{predicate_name}: {len(bad)} item(s) failed")

    if failures:
        bullet_list = "\n".join(f"  - {f}" for f in failures)
        raise VerificationError(f"assert_list({path}): {len(failures)} check(s) failed:\n{bullet_list}")


def assert_body_empty(resp: ApiResponse) -> None:
    """No response body -- e.g. a 204 No Content on delete. Passes on an
    empty string as well as whitespace-only text, since servers sometimes
    pad an otherwise-empty body with a trailing newline."""
    passed = not resp.text.strip()
    display_actual = "<empty>" if passed else resp.text
    record = AssertionRecord("assert_body_empty", passed, "<empty>", display_actual, "body")
    _verify(record, f"expected empty body, got {display_actual!r}")


def assert_response_time(resp: ApiResponse, ms: float) -> None:
    """Latency budget as a first-class check, not an afterthought."""
    passed = resp.elapsed_ms <= ms
    record = AssertionRecord(f"assert_response_time(<= {ms}ms)", passed, f"<= {ms}ms", f"{resp.elapsed_ms:.0f}ms", "latency")
    _verify(record, f"response took {resp.elapsed_ms:.0f}ms, over the {ms}ms budget")
