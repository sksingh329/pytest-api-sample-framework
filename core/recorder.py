"""The evidence ledger. Binds the active test id, appends records to a
per-worker JSONL stream (append-only, streamable, mergeable), and preserves
ordering so requests and assertions interleave exactly as they happened.

Log levels are additive and control how much evidence each RECORD carries
(not what runs): ERROR keeps evidence only for failing tests; WARNING adds
retried attempts and over-budget latency for passing tests too; INFO (the
default) keeps every request/assertion for every test; DEBUG adds redacted
headers/bodies; TRACE adds every retry attempt. See README for the full
table -- this module is where that table is actually enforced.
"""
from __future__ import annotations

import contextvars
import json
import threading
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from core.config import Settings
from core.http_client import RequestRecord
from core import redaction

if TYPE_CHECKING:  # avoid a core.recorder <-> core.assertions import cycle
    from core.assertions import AssertionRecord

_LEVEL_RANK = {"ERROR": 0, "WARNING": 1, "INFO": 2, "DEBUG": 3, "TRACE": 4}

# The currently-active Recorder for *this* test, in *this* process. ApiClient
# is session-scoped and doesn't know which test is running; it always writes
# through RecorderProxy, which looks up whichever Recorder is bound here.
_active: "contextvars.ContextVar[Recorder | None]" = contextvars.ContextVar("active_recorder", default=None)


def get_active_recorder() -> "Recorder | None":
    return _active.get()


class LedgerWriter:
    """Owns the append-only JSONL file handle for one worker process for the
    whole session. Truncated fresh at the start of each session (a new
    `pytest` invocation is a new run, not a continuation of the last one --
    otherwise a stale ledger from a previous run would corrupt this run's
    start/end timestamps); append-only and line-flushed *within* that
    session, so a killed run still leaves a readable partial log on disk."""

    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self._path = path
        self._fh = open(path, "w", buffering=1, encoding="utf-8")
        self._lock = threading.Lock()

    def write(self, entry: dict) -> None:
        line = json.dumps(entry, default=str)
        with self._lock:
            self._fh.write(line + "\n")
            self._fh.flush()

    def close(self) -> None:
        with self._lock:
            self._fh.close()


class RecorderProxy:
    """Handed to ApiClient at session scope. Forwards to whichever Recorder
    is bound to the currently-running test via the contextvar above."""

    def record_request(self, record: RequestRecord) -> None:
        recorder = _active.get()
        if recorder is not None:
            recorder.record_request(record)


class Recorder:
    """One per test. Buffers everything the test produces, then decides at
    finish() what actually gets written based on api_log_level and outcome
    -- so the filtering rule lives in exactly one place.
    """

    def __init__(self, test_id: str, ledger: LedgerWriter, settings: Settings):
        self._test_id = test_id
        self._ledger = ledger
        self._settings = settings
        self._buffer: list[tuple[str, dict]] = []
        self._suite = ""
        self._marker = ""
        self._phase = "setup"  # core.plugin advances this through "test" -> "teardown"
        self._token: contextvars.Token | None = None

    def __enter__(self) -> "Recorder":
        self._token = _active.set(self)
        return self

    def __exit__(self, *exc) -> None:
        if self._token is not None:
            _active.reset(self._token)

    def start(self, suite: str, marker: str) -> None:
        self._suite = suite
        self._marker = marker
        self._buffer.append(("test_start", {"suite": suite, "marker": marker, "ts": time.time()}))

    def set_phase(self, phase: str) -> None:
        """"setup" | "test" | "teardown" -- stamped on every request/assertion
        recorded from here on, so the report's runner log can show which
        part of the test produced a given call (arrange vs. act vs.
        cleanup). Set by core.plugin as pytest moves through setup/call/
        teardown for the active test."""
        self._phase = phase

    def record_request(self, record: RequestRecord) -> None:
        settings = self._settings
        include_body = _LEVEL_RANK[settings.api_log_level] >= _LEVEL_RANK["DEBUG"]
        entry = {
            "request_id": record.request_id,
            "attempt": record.attempt,
            "max_attempts": record.max_attempts,
            "method": record.method,
            "url": record.url,
            "path": _relative_path(record.url, settings.base_url),
            "service": record.service,
            "status_code": record.status_code,
            "duration_ms": round(record.duration_ms, 1),
            "error": record.error,
            "retryable": record.retryable,
            "final_attempt": record.attempt == record.max_attempts or not record.retryable,
            "phase": self._phase,
            "ts": time.time(),
        }
        if include_body:
            entry["request_headers"] = redaction.redact_mapping(record.request_headers, settings.api_redact_keys)
            entry["request_body"] = redaction.prepare_body(record.request_body, settings.api_redact_keys, settings.api_max_body_chars)
            entry["response_headers"] = redaction.redact_mapping(record.response_headers, settings.api_redact_keys)
            entry["response_body"] = redaction.prepare_body(record.response_body, settings.api_redact_keys, settings.api_max_body_chars)
        else:
            entry["response_body"] = None  # size still derivable from response_size below

        try:
            entry["response_size"] = len(json.dumps(record.response_body, default=str)) if record.response_body is not None else 0
        except TypeError:
            entry["response_size"] = 0

        self._buffer.append(("request", entry))

    def record_assertion(self, record: "AssertionRecord") -> None:
        entry = {
            "name": record.name,
            "passed": record.passed,
            "expected": record.expected,
            "actual": record.actual,
            "kind": record.kind,
            "violations": record.violations,
            "phase": self._phase,
            "ts": time.time(),
        }
        self._buffer.append(("assertion", entry))

    def finish(self, outcome: str) -> None:
        for kind, entry in self._filter_for_level(outcome):
            entry = dict(entry)
            entry["type"] = kind
            entry["test_id"] = self._test_id
            self._ledger.write(entry)
        self._ledger.write({
            "type": "test_end",
            "test_id": self._test_id,
            "suite": self._suite,
            "marker": self._marker,
            "outcome": outcome,
            "ts": time.time(),
        })

    # -- level filtering --------------------------------------------------

    def _filter_for_level(self, outcome: str):
        level = self._settings.api_log_level
        rank = _LEVEL_RANK[level]

        for kind, entry in self._buffer:
            if kind == "test_start":
                yield kind, entry
                continue

            if outcome == "fail":
                # a failed test keeps its full trail regardless of level --
                # that trail *is* the evidence for why it failed.
                if kind == "request" and not entry.get("final_attempt", True) and rank < _LEVEL_RANK["TRACE"]:
                    continue  # intermediate retry attempts only at TRACE
                yield kind, entry
                continue

            # passing/skipped test
            if rank == _LEVEL_RANK["ERROR"]:
                continue  # ERROR: failed tests only

            if kind == "assertion":
                if rank >= _LEVEL_RANK["INFO"] or not entry["passed"]:
                    yield kind, entry
                continue

            if kind == "request":
                over_budget = entry["duration_ms"] > self._settings.api_latency_budget_ms
                was_retried = not entry.get("final_attempt", True)
                if rank >= _LEVEL_RANK["INFO"]:
                    if was_retried and rank < _LEVEL_RANK["TRACE"]:
                        continue  # intermediate attempts only at TRACE
                    yield kind, entry
                elif rank == _LEVEL_RANK["WARNING"] and (over_budget or was_retried):
                    yield kind, entry


def _relative_path(url: str, base_url: str) -> str:
    return url[len(base_url):] if url.startswith(base_url) else url
