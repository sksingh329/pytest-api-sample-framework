# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

Setup (no packaging/build step — `core/` and `api/` are imported straight off the repo root):
```bash
cp .env.example .env             # fill in DEV_DEFAULT_TOKEN at minimum
pip install -r requirements-test.txt
```

Run tests:
```bash
pytest                                    # full suite, pytest.ini defaults (api_env=dev)
pytest tests/users/test_users.py          # one file
pytest tests/users/test_users.py::test_create_user   # one test
pytest -m smoke                           # marker filter: smoke | regression | contract
API_ENV=stage pytest                      # any pytest.ini key can be overridden via API_<KEY>
API_LOG_LEVEL=TRACE pytest                # full evidence incl. every retry attempt
```

There is no lint/build/typecheck command configured in this repo.

After a run, check `reports/<api_env>/<timestamp>/report.html` for the full per-test evidence
trail, or `reports/<api_env>/index.html` for run history.

## Architecture

Full narrative writeup: [docs/FRAMEWORK_NOTES.md](docs/FRAMEWORK_NOTES.md).

**Two layers, don't blur them:** `core/` is the framework engine (config, HTTP client, assertions,
recording/reporting) and is never imported directly by tests. `api/` is the API-under-test layer
(services, payload builders, schemas) that tests do use. Adding a new resource means adding files
under `api/`, not touching `core/`.

**Request flow:** test → `*_service` fixture ([tests/conftest.py](tests/conftest.py)) →
`BaseService._get/_post/...` ([api/base_service.py](api/base_service.py)) → `ApiClient.request()`
([core/http_client.py](core/http_client.py)) — injects the bearer token, retries transient
statuses (429/502/503/504) with backoff, times the call, returns an `ApiResponse` (never a raw
`requests.Response`) → `RecorderProxy` forwards a `RequestRecord` to whichever `Recorder` is bound
to the currently-running test via a `contextvars` context (`ApiClient` is session-scoped and has
no notion of "current test") → buffered, then filtered by `api_log_level` and written to that
xdist worker's JSONL ledger at test end.

**Assertions are mandatory, bare `assert` is not used:** every check in
[core/assertions.py](core/assertions.py) (`assert_status`, `assert_field`, `assert_schema`,
`assert_list`, `assert_response_time`, ...) logs an `AssertionRecord` to the active recorder
*before* raising, so the HTML report shows every check a test performed, pass or fail. A bare
`assert` produces no record and silently vanishes from the report — always assert through this
module. `VerificationError` subclasses `AssertionError` so failures still render as normal pytest
failures.

**Config resolution order:** `pytest.ini` → `environments.py`'s `ENVIRONMENTS[api_env]` dict →
env var overrides (`API_<KEY>` for ini keys, `API_BASE_URL` for the environment block), merged
into one frozen `Settings` in [core/config.py](core/config.py) at collection time. Auth has no
login flow — `TokenProvider` ([core/auth.py](core/auth.py)) reads a fixed bearer token from
`<API_ENV>_<ROLE>_TOKEN` (e.g. `DEV_DEFAULT_TOKEN`), loaded from a gitignored `.env` via the root
[conftest.py](conftest.py).

**Schema contracts are pydantic, not JSON Schema files:** each `api/schemas/*.py` module exports a
module-level `SCHEMAS = {name: Model}` dict; `SchemaRegistry` ([core/schemas.py](core/schemas.py))
auto-indexes every such module under `api_schema_dir` once per session. `assert_schema(resp,
"name")` validates against it; models use `ConfigDict(extra="forbid")` so both missing and
unexpected fields are flagged as contract drift.

**xdist safety:** each worker writes its own `reports/<env>/ledger/<worker>.jsonl`. Only the
controller process (no `workerinput` attr) merges ledgers and renders `report.html` /
`index.html` / `history.json`, in `pytest_terminal_summary`
([core/plugin.py](core/plugin.py)) — never a worker.

**Adding a new resource** (endpoints → service → payload builder → schema → fixture → tests) is
documented step-by-step in [docs/FRAMEWORK_NOTES.md](docs/FRAMEWORK_NOTES.md#3-how-to-write-tests).
