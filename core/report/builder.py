"""merged ledger -> run model.

Kept separate from renderer.py so the model itself (a plain dict matching
the schema documented in the README / spec) is unit-testable without
touching Jinja or HTML at all.
"""
from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path
from typing import Any

from core.config import Settings

_HISTORY_KEEP = 12


def load_fixture() -> dict:
    """Load the hand-authored sample run model used to preview the report
    without running the suite. Same shape build_run_model() produces."""
    return json.loads((Path(__file__).parent / "sample_run_model.json").read_text())


def build_run_model(
    ledger_paths: list[Path],
    settings: Settings,
    exitstatus: int = 0,
    run_folder: str | None = None,
    command: str | None = None,
) -> dict:
    """Merge one or more per-worker JSONL ledgers (see core.recorder) into
    one run model dict, tests ordered by first-seen and each test's own
    requests/assertions kept in the chronological order they were recorded.

    run_folder is this run's own timestamped output folder name (e.g.
    "20260822-084026", from core.plugin), recorded on both meta.runFolder
    and this run's history.json entry so the report can link to/from its
    sibling runs. command is the exact `pytest ...` invocation that
    produced this run (see core.plugin.pytest_configure), shown in the
    report so a run is reproducible from the report alone. Both optional
    -- omitted for fixture/unit-test previews where there's no real
    invocation or output folder.
    """
    tests: dict[str, dict] = {}
    order: list[str] = []
    run_start = None
    run_end = None

    for path in ledger_paths:
        for entry in _read_jsonl(path):
            test_id = entry.get("test_id")
            kind = entry["type"]
            ts = entry.get("ts")
            if ts is not None:
                run_start = ts if run_start is None else min(run_start, ts)
                run_end = ts if run_end is None else max(run_end, ts)

            if test_id is None:
                continue
            if test_id not in tests:
                tests[test_id] = _new_test(test_id)
                order.append(test_id)
            slot = tests[test_id]

            if kind == "test_start":
                slot["suite"] = entry.get("suite", "")
                slot["marker"] = entry.get("marker", "unmarked")
            elif kind == "request":
                slot["_requests"].append(entry)
            elif kind == "assertion":
                slot["_assertions"].append(entry)
            elif kind == "test_end":
                slot["outcome"] = entry.get("outcome", "pass")

    test_models = [_finalize_test(tests[tid]) for tid in order]
    duration_ms = int((run_end - run_start) * 1000) if run_start and run_end else 0

    history = _update_history(settings, test_models, duration_ms, run_folder)

    meta = {
        "runNumber": history[-1]["run"] if history else 1,
        "runFolder": run_folder,
        "command": command or "pytest",
        "branch": _git("rev-parse", "--abbrev-ref", "HEAD") or "unknown",
        "commit": _git("rev-parse", "--short", "HEAD") or "unknown",
        "environment": settings.api_env,
        "baseUrl": settings.base_url,
        "runner": f"pytest / api-test-core (log level {settings.api_log_level})",
        "logLevel": settings.api_log_level,
        "startTime": _iso(run_start) if run_start else _iso(time.time()),
        "durationMs": duration_ms,
        "workerCount": len(ledger_paths),
        "retries": settings.api_retries,
        "timeoutSeconds": settings.api_timeout,
        "authMode": "bearer",
        "maskedToken": "n/a",
        "artifactRetentionDays": 14,
        "previousPassRate": history[-2]["passed"] / max(1, sum(history[-2][k] for k in ("passed", "failed", "skipped"))) if len(history) >= 2 else None,
        "latencyBudgetMs": settings.api_latency_budget_ms,
    }

    return {"meta": meta, "history": history, "tests": test_models}


def _new_test(test_id: str) -> dict:
    return {"id": test_id, "suite": "", "marker": "unmarked", "outcome": "pass", "_requests": [], "_assertions": []}


def _finalize_test(slot: dict) -> dict:
    requests = slot["_requests"]
    assertions = slot["_assertions"]
    # one entry per distinct HTTP call the test made (deduped by
    # request_id, keeping each call's final attempt), in the order each
    # call was first made -- a test doing arrange-then-act often makes
    # more than one, and the report should show all of them, not just
    # the last.
    calls = _group_calls(requests)
    primary = calls[-1] if calls else None

    test_name = slot["id"].split("::")[-1]

    logs = []
    for r in requests:
        level = "error" if r.get("error") else ("warn" if r.get("retryable") and not r.get("final_attempt") else "info")
        msg = (
            f"{r['method']} {r['path']} -> {r.get('status_code')} "
            f"({r['duration_ms']}ms, attempt {r['attempt']}/{r['max_attempts']})"
            if not r.get("error") else
            f"{r['method']} {r['path']} -> ERROR ({r['error']}), attempt {r['attempt']}/{r['max_attempts']}"
        )
        logs.append({"ts": _short_ts(r.get("ts")), "_sort_ts": r.get("ts") or 0, "level": level, "phase": r.get("phase", "test"), "message": msg})
    for a in assertions:
        logs.append({
            "ts": _short_ts(a.get("ts")),
            "_sort_ts": a.get("ts") or 0,
            "level": "pass" if a["passed"] else "fail",
            "phase": a.get("phase", "test"),
            "message": f"{a['name']}: expected {a['expected']}, got {a['actual']}",
        })
    # sort by the real (sub-second) timestamp, not the display string --
    # _short_ts() only has whole-second precision, so several lines landing
    # in the same second would otherwise fall back to insertion order
    # (all requests, then all assertions) instead of what actually happened
    # first.
    logs.sort(key=lambda l: l["_sort_ts"])
    for l in logs:
        del l["_sort_ts"]

    return {
        "id": slot["id"],
        "testName": test_name,
        "suite": slot["suite"] or test_name,
        "marker": slot["marker"],
        "service": primary.get("service") if primary else None,
        "method": primary.get("method") if primary else None,
        "path": primary.get("path") if primary else None,
        "statusCode": primary.get("status_code") if primary else None,
        "durationMs": primary.get("duration_ms") if primary else None,
        "responseSize": primary.get("response_size", 0) if primary else 0,
        "outcome": slot["outcome"],
        "assertions": [
            {
                "name": a["name"], "passed": a["passed"], "expected": a["expected"],
                "actual": a["actual"], "kind": a["kind"], "violations": a.get("violations"),
            }
            for a in assertions
        ],
        "calls": [
            {
                "method": c.get("method"),
                "path": c.get("path"),
                "statusCode": c.get("status_code"),
                "durationMs": c.get("duration_ms"),
                "attempt": c.get("attempt"),
                "maxAttempts": c.get("max_attempts"),
                "request": _request_view(c),
                "response": _response_view(c),
            }
            for c in calls
        ],
        "logs": logs,
    }


def _group_calls(requests: list[dict]) -> list[dict]:
    """Collapse every buffered attempt down to one entry per distinct call
    (request_id). Attempts for one call are appended in order (1, 2, 3...),
    so the last entry seen for a given request_id is always its final
    attempt -- no need to check the final_attempt flag here."""
    order: list[str] = []
    last_by_id: dict[str, dict] = {}
    for r in requests:
        rid = r.get("request_id")
        if rid not in last_by_id:
            order.append(rid)
        last_by_id[rid] = r
    return [last_by_id[rid] for rid in order]


def _request_view(r: dict) -> dict:
    return {
        "url": r.get("url"),
        "headers": r.get("request_headers"),
        "body": r.get("request_body"),
        "attempt": r.get("attempt"),
    }


def _response_view(r: dict) -> dict:
    return {"headers": r.get("response_headers"), "body": r.get("response_body")}


def _read_jsonl(path: Path):
    if not path.exists():
        return
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue  # a killed run can leave one partial trailing line


def _update_history(settings: Settings, test_models: list[dict], duration_ms: int, run_folder: str | None) -> list[dict]:
    # per-environment, NOT inside a timestamped run folder -- history has to
    # survive across runs for the chart to have anything to show.
    history_path = settings.api_report_dir / settings.api_env / "history.json"
    history: list[dict] = []
    if history_path.exists():
        try:
            history = json.loads(history_path.read_text())
        except json.JSONDecodeError:
            history = []

    next_run = (history[-1]["run"] + 1) if history else 1
    outcomes = [t["outcome"] for t in test_models]
    history.append({
        "run": next_run,
        "passed": outcomes.count("pass"),
        "failed": outcomes.count("fail"),
        "skipped": outcomes.count("skip"),
        "durationMs": duration_ms,
        "folder": run_folder,  # None for fixture/preview runs -- just not clickable
    })
    history = history[-_HISTORY_KEEP:]

    history_path.parent.mkdir(parents=True, exist_ok=True)
    history_path.write_text(json.dumps(history, indent=2))
    return history


def _git(*args: str) -> str | None:
    try:
        return subprocess.check_output(["git", *args], stderr=subprocess.DEVNULL, text=True).strip() or None
    except Exception:
        return None


def _iso(ts: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts))


def _short_ts(ts: float | None) -> str:
    return time.strftime("%H:%M:%S", time.localtime(ts)) if ts else ""
