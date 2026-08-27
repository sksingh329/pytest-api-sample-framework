# Framework Notes — pytest API Sample Framework

A pytest-based API test framework (currently exercised against `gorest.in`). No packaging/install
step: `core/` and `api/` are plain packages imported straight off the repo root, added to
`sys.path` by the presence of the root [conftest.py](conftest.py).

## 1. What it does (features)

- **Config resolution** — pytest.ini + `environments.py` + env-var overrides, merged into one
  frozen, validated `Settings` object at collection time (fails fast with a readable error instead
  of failing mid-run).
- **Pooled, retrying HTTP client** — `ApiClient` wraps `requests.Session` with connection pooling,
  manual retries (429/502/503/504, exponential backoff), bearer-token injection, and a uniform
  `ApiResponse` wrapper (tests never see a raw `requests.Response`).
- **Fixed bearer-token auth, per role** — no login flow. Tokens are read once from
  `<API_ENV>_<ROLE>_TOKEN` env vars (populated via a gitignored `.env`) and cached in memory.
- **Rich, typed assertions** (`core/assertions.py`) — status, field (dotted/indexed path), field
  presence, header, header presence, schema, list (length/uniqueness/sort/predicate), response
  time, plus `soft_assertions()` to collect multiple failures before raising once. Every check is
  logged as an `AssertionRecord` *before* it raises, so a bare `assert` is disallowed by
  convention — always go through these.
- **Schema/contract validation** — `SchemaRegistry` indexes plain pydantic models declared in
  `api/schemas/*.py` (a `SCHEMAS = {name: Model}` dict per file) and validates responses against
  them via `assert_schema(resp, "name")`, catching both missing fields and unexpected ones
  (`extra="forbid"`).
- **Evidence ledger + HTML report** — every request (incl. every retry attempt) and every
  assertion is recorded per-test to an append-only JSONL ledger, then merged and rendered into an
  HTML report at session end (`core/report/`), with a history page across the last runs.
- **Configurable verbosity** — `api_log_level` (ERROR/WARNING/INFO/DEBUG/TRACE) controls how much
  evidence is kept per record (not what runs): from "only failing tests" up to "every retry
  attempt with full headers/bodies."
- **Redaction** — configured keys (`authorization, password, token` by default) are masked in
  headers/bodies before anything touches disk, at any nesting depth; oversized bodies are
  truncated with an explicit marker.
- **xdist-safe** — one ledger file per worker, merged only by the controller process at session
  finish; report is rendered exactly once.
- **Test data builders** — `api/payloads/*.py` build valid request bodies with sane random
  defaults (deterministic under a seed) and an `OMIT` sentinel for negative-test field removal.
- **Cleanup fixtures** — `created_user` / `cleanup_users` in [tests/conftest.py](tests/conftest.py)
  delete anything a test created, pass or fail, so the target API doesn't accumulate test data.

## 2. Architecture

```
conftest.py                 # sys.path root, loads .env, registers core.plugin
pytest.ini                  # ini options (api_env, timeouts, log level, ...) + markers
environments.py             # ENVIRONMENTS[api_env] -> {BASE_URL: ...}

core/                        # framework internals — tests never import these directly
  config.py                  # pytest.ini + environments.py + env vars -> frozen Settings
  auth.py                    # TokenProvider: <ENV>_<ROLE>_TOKEN -> bearer token, cached
  http_client.py             # ApiClient (pooled session, retries) + ApiResponse + RequestRecord
  assertions.py               # assert_status/field/header/schema/list/response_time, soft_assertions
  schemas.py                  # SchemaRegistry: indexes api/schemas/*.py pydantic models
  recorder.py                  # Recorder (per test) + LedgerWriter (per worker) + level filtering
  redaction.py                 # mask secret keys, truncate oversized bodies
  plugin.py                    # pytest hooks: wires Settings, opens/closes Recorder per test,
                                # renders the report at session finish
  errors.py                    # ConfigError, TransportError, VerificationError(AssertionError)
  report/
    builder.py                 # ledger JSONL -> run_model dict
    renderer.py                 # run_model -> report.html / index.html (Jinja2)
    template.html.j2

api/                          # the thing under test — one folder per resource, in your control
  base_service.py              # BaseService: _get/_post/_put/_patch/_delete over an ApiClient
  constants.py                  # endpoints, roles
  users_service.py               # UsersService(BaseService): one method per business action
  payloads/users_payloads.py     # build_user(...) request-body builder
  schemas/users.py                # User / ValidationErrorItem pydantic models -> SCHEMAS dict

tests/
  conftest.py                   # settings/token_provider/api_client/*_service fixtures
  users/test_users.py            # actual test cases

reports/<env>/<timestamp>/       # report.html, summary.json per run
reports/<env>/ledger/*.jsonl     # per-worker evidence ledgers
reports/<env>/history.json       # last N runs, for the report's history chart
reports/<env>/index.html         # entry point listing every run
```

### Request flow (one call)
`test` → `*_service` fixture (e.g. `users_service`) → `BaseService._get/_post/...` →
`ApiClient.request()` (injects bearer token, retries, times, wraps as `ApiResponse`) →
`RecorderProxy` forwards a `RequestRecord` to whichever `Recorder` is bound to the currently
running test (via a `contextvars` context, since `ApiClient` is session-scoped and doesn't know
which test is running) → `Recorder` buffers it → at test end, `Recorder.finish()` filters by
`api_log_level` and outcome, then writes to that worker's JSONL ledger.

### Assertion flow
`core.assertions.assert_*()` builds an `AssertionRecord`, sends it to the active `Recorder`
**before** raising — so both passing and (per level) failing checks land in the evidence trail,
and a failure surfaces as a normal pytest `AssertionError` (via `VerificationError`), not an
internal error.

### Session-end flow
`pytest_sessionfinish` closes the ledger; `pytest_terminal_summary` (controller process only —
xdist workers skip this) merges every worker's `*.jsonl`, builds a `run_model`, and writes
`report.html`, `summary.json`, and an updated `index.html`/`history.json`.

## 3. How to write tests

### One-time setup
```bash
cp .env.example .env
# fill in DEV_DEFAULT_TOKEN (and DEV_READ_TOKEN / DEV_WRITE_TOKEN if you use roles)
pip install -r requirements-test.txt
```

### Running
```bash
pytest                          # uses pytest.ini defaults (api_env=dev, etc.)
pytest -m smoke                 # marker-filtered
API_ENV=stage pytest            # env-var override, no ini edit needed
```

### Adding a new resource (e.g. "posts")
1. **Endpoints** — add a class to [api/constants.py](api/constants.py) (`PostsEndpoints`), same
   shape as `UsersEndpoints`.
2. **Service** — add `api/posts_service.py`, subclass `BaseService`, set `service_name`, add one
   method per business action, always returning `ApiResponse`:
   ```python
   class PostsService(BaseService):
       service_name = "posts"
       def create_post(self, **body) -> ApiResponse:
           return self._post(PostsEndpoints.BASE, json=body)
   ```
3. **Payload builder** — add `api/payloads/posts_payloads.py` with a `build_post(**overrides)`
   function, following `build_user`'s pattern (deterministic under `_seed`, `OMIT` for negative
   tests).
4. **Schema** — add `api/schemas/posts.py` with pydantic models and a module-level
   `SCHEMAS = {"post": Post, "posts_list": list[Post]}` dict; the registry auto-indexes it.
5. **Fixture** — add a `posts_service` fixture to [tests/conftest.py](tests/conftest.py):
   ```python
   @pytest.fixture
   def posts_service(api_client: ApiClient) -> PostsService:
       return PostsService(api_client)
   ```
   Add a cleanup fixture too if creates need to be torn down.
6. **Tests** — add `tests/posts/test_posts.py`.

### Writing a test case
Arrange via fixtures, act via the service, verify via `core.assertions` only:
```python
from api.payloads.users_payloads import build_user
from core.assertions import assert_status, assert_schema, assert_field

def test_create_user(users_service, cleanup_users):
    response = users_service.create_user(**build_user())
    cleanup_users.append(response.json()["id"])

    assert_status(response, 201)
    assert_schema(response, "user")
    assert_field(response, "email", response.request_body["email"])
```

Guidelines:
- Never use a bare `assert` — it produces no evidence record and silently disappears from the
  report. Always go through `core.assertions`.
- Use `soft_assertions()` when a test needs to check several independent things and report all
  failures at once, not stop at the first.
- Mark tests with `@pytest.mark.smoke` / `regression` / `contract` (declared in
  [pytest.ini](pytest.ini)) so `-m` filtering and the report's grouping work.
- For negative tests, build a bad payload with the same builder plus `OMIT`, e.g.
  `build_user(email=OMIT)`.
- Use `assert_response_time(resp, ms)` for latency budgets instead of hand-rolled timing checks.
- Clean up anything you create — use/extend a `cleanup_*` fixture rather than deleting inline, so
  cleanup still runs on failure.

### After a run
Check `reports/<api_env>/<timestamp>/report.html` for the full per-test evidence trail (requests,
retries, assertions, timings), or `reports/<api_env>/index.html` for the run history.
