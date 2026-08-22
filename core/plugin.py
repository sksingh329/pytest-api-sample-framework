"""pytest integration: registers ini options/markers, opens and closes a
per-test Recorder around setup/call/teardown, and at session finish merges
every worker's ledger and renders the report -- in the controller process
only (xdist workers each hold a partial view and must never render).
"""
from __future__ import annotations

import json
import os
import time

import pytest

from core.config import load_settings
from core.errors import ConfigError
from core.recorder import LedgerWriter, Recorder

_INI_HELP = {
    "api_env": "selects environments.ENVIRONMENTS[api_env] to resolve base_url/auth from (dev|stage|prod)",
    "api_log_level": "evidence detail per record: ERROR|WARNING|INFO|DEBUG|TRACE",
    "api_timeout": "per-request timeout in seconds",
    "api_retries": "attempts for transport errors and retryable statuses",
    "api_report_dir": "output dir for report.html, summary.json, raw ledgers",
    "api_redact_keys": "comma-separated keys masked before anything is written",
    "api_max_body_chars": "body truncation cap, with explicit marker",
    "api_latency_budget_ms": "threshold (ms) that emits a latency warning record",
    "api_schema_dir": "root dir the SchemaRegistry indexes contracts from",
}


def pytest_addoption(parser):
    for key, help_text in _INI_HELP.items():
        parser.addini(key, help=help_text, default=None)


def pytest_configure(config):
    for marker in ("smoke", "regression", "contract"):
        config.addinivalue_line("markers", f"{marker}: see pytest.ini")

    try:
        settings = load_settings(config)
    except ConfigError as exc:
        # surface as a clean fail-fast usage error, not an INTERNALERROR
        # traceback -- config problems are the user's to fix, not a bug.
        raise pytest.UsageError(f"api-test-core config error: {exc}") from exc
    config._api_settings = settings
    # the exact invocation, for the report's "Command" section -- lets
    # anyone looking at a report reproduce the run instead of guessing
    # which markers/paths/flags produced it.
    config._api_command = "pytest " + " ".join(config.invocation_params.args)

    worker_id = os.environ.get("PYTEST_XDIST_WORKER", "master")
    ledger_path = settings.api_report_dir / settings.api_env / "ledger" / f"{worker_id}.jsonl"
    config._api_ledger = LedgerWriter(ledger_path)

    import core.schemas as _schemas_module

    try:
        _schemas_module.configure(settings.api_schema_dir)
    except ConfigError as exc:
        raise pytest.UsageError(f"api-test-core config error: {exc}") from exc


def pytest_runtest_setup(item):
    settings = item.config._api_settings
    recorder = Recorder(item.nodeid, item.config._api_ledger, settings)
    marker = next((m for m in ("smoke", "regression", "contract") if item.get_closest_marker(m)), "unmarked")
    suite = item.nodeid.split("::", 1)[0]
    recorder.start(suite=suite, marker=marker)
    recorder.__enter__()
    item._api_recorder = recorder
    item._api_outcome = "pass"


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_call(item):
    # code before `yield` in a hookwrapper always runs before every other
    # (non-wrapper) implementation, including the one that actually invokes
    # the test function -- so this reliably flips the phase to "test"
    # before the test body's own requests/assertions happen, regardless of
    # plugin registration order.
    recorder = getattr(item, "_api_recorder", None)
    if recorder is not None:
        recorder.set_phase("test")
    yield


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    # Standard pytest pattern: stash each phase's TestReport on the item so
    # pytest_runtest_teardown (below) can read the real setup/call outcome
    # -- by teardown time, setup's and call's makereport have both already run.
    outcome = yield
    rep = outcome.get_result()
    setattr(item, f"_api_rep_{rep.when}", rep)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_teardown(item, nextitem):
    # hookwrapper, not a plain hookimpl: pytest's own teardown work (running
    # every fixture's post-yield code, e.g. a cleanup fixture's delete_user
    # call) happens in OTHER pytest_runtest_teardown implementations, whose
    # relative order against a plain hookimpl here isn't guaranteed. As a
    # plain hookimpl this closed the recorder (detaching the "active
    # recorder" contextvar) *before* fixture teardown ran in some orderings
    # -- so a delete made during fixture teardown had no recorder to write
    # to and silently vanished from the ledger. `yield` first guarantees
    # every other implementation (including all fixture teardown) finishes
    # before we close the recorder, no matter the registration order.
    recorder = getattr(item, "_api_recorder", None)
    if recorder is not None:
        recorder.set_phase("teardown")  # before yield: takes effect before fixture teardown runs

    yield

    if recorder is None:
        return
    setup_rep = getattr(item, "_api_rep_setup", None)
    call_rep = getattr(item, "_api_rep_call", None)
    if setup_rep is not None and setup_rep.skipped:
        outcome = "skip"
    elif setup_rep is not None and setup_rep.failed:
        outcome = "fail"
    elif call_rep is not None and call_rep.failed:
        outcome = "fail"
    elif call_rep is not None and call_rep.skipped:
        outcome = "skip"
    else:
        outcome = "pass"
    recorder.finish(outcome)
    recorder.__exit__()


def pytest_sessionfinish(session, exitstatus):
    config = session.config
    ledger = getattr(config, "_api_ledger", None)
    if ledger is not None:
        ledger.close()


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    # xdist workers each hold only their own slice of the run; only the
    # controller process (no `workerinput` attribute) renders the report.
    if hasattr(config, "workerinput"):
        return

    settings = getattr(config, "_api_settings", None)
    if settings is None:
        return

    from core.report.builder import build_run_model
    from core.report.renderer import render_html, render_index_html

    ledger_dir = settings.api_report_dir / settings.api_env / "ledger"
    ledger_paths = sorted(ledger_dir.glob("*.jsonl")) if ledger_dir.exists() else []
    if not ledger_paths:
        return

    # one timestamped folder per run, so nothing overwrites a previous run's
    # report/summary: reports/<env>/<YYYYmmdd-HHMMSS>/{report.html,summary.json}
    # -- computed before build_run_model so this run's own history.json entry
    # (and meta.runFolder) know the folder the report is about to land in.
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    command = getattr(config, "_api_command", "pytest")
    run_model = build_run_model(ledger_paths, settings, exitstatus=exitstatus, run_folder=timestamp, command=command)

    run_dir = settings.api_report_dir / settings.api_env / timestamp
    run_dir.mkdir(parents=True, exist_ok=True)
    report_path = run_dir / "report.html"
    summary_path = run_dir / "summary.json"

    report_path.write_text(render_html(run_model))

    outcomes = [t["outcome"] for t in run_model["tests"]]
    summary = {
        "runNumber": run_model["meta"]["runNumber"],
        "total": len(outcomes),
        "passed": outcomes.count("pass"),
        "failed": outcomes.count("fail"),
        "skipped": outcomes.count("skip"),
        "environment": run_model["meta"]["environment"],
        "durationMs": run_model["meta"]["durationMs"],
    }
    summary_path.write_text(json.dumps(summary, indent=2))

    # one stable entry point listing every run in the history window --
    # regenerated every time from the same history.json the chart reads.
    index_path = settings.api_report_dir / settings.api_env / "index.html"
    index_path.write_text(render_index_html(settings.api_env, run_model["history"]))

    terminalreporter.write_sep("-", "api-test-core report")
    terminalreporter.write_line(f"report: {report_path}")
    terminalreporter.write_line(f"summary: {summary_path}")
    terminalreporter.write_line(f"index: {index_path}")
