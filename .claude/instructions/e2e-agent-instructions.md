# E2E Agent Instructions

This framework is API-only (gorest.in) — there is no UI/browser layer. "E2E" here
means a **multi-step workflow test**: a scenario that chains multiple API calls to
exercise a realistic user journey end-to-end (e.g. create → read → update → delete
a resource, or a flow spanning more than one service), as opposed to a single-call
test that only checks one request/response in isolation.

This document is the reference all QA Agent skills (testcase-writer, test-plan,
test-setup, test-creator) must follow for E2E scenarios in this repo, instead of
inventing new conventions per feature.

## When a scenario is "E2E"

A test belongs in the E2E category when it depends on the outcome of a *previous*
call in the same test to make its next call meaningful — e.g. the id from a create
response is used in a subsequent get/update/delete. A test that only issues one
call (even if it asserts many things about the response) is not E2E; it belongs
alongside the existing single-call tests (see [tests/users/test_users.py](../tests/users/test_users.py),
[tests/users/test_users_auth.py](../tests/users/test_users_auth.py)).

## File & directory layout

- E2E tests live under `tests/<feature>/`, alongside that feature's other tests —
  there is no separate `tests/e2e/` tree. Group by feature/module, not by
  test type.
- File naming: `test_<feature>_e2e.py` (e.g. `tests/users/test_users_e2e.py`),
  mirroring the existing `test_<feature>.py` / `test_<feature>_auth.py` pattern.
- Every test is a method inside a class — pipeline-generated code has no standalone
  `test_*` functions. All E2E tests for one file share one class; see "Naming" below
  for the class name. (The hand-written files this pattern mirrors — `test_users.py`,
  `test_users_auth.py` — predate this convention and stay as plain functions;
  `test-creator` never retrofits them, it only ever writes new files this way.)

## Build order for a new resource

An E2E scenario is never coded straight into the test file. Before any test is
written, the support layer for every resource the journey touches must already
exist.

**The order is the one documented in
[docs/FRAMEWORK_NOTES.md](FRAMEWORK_NOTES.md#3-how-to-write-tests) —
"Adding a new resource": endpoints → service → payload builder → schema →
fixture → test.** That is the single source of truth for the order; don't
restate or re-derive it here.

Who builds what:

- Steps 1–5 (endpoints, service, payload builder, schema, fixture) belong to
  the **`test-setup`** skill, which builds them after mandatory user approval.
- Step 6 (the test itself) belongs to **`test-creator`**, which writes only
  `tests/<feature>/test_*.py`.

If any of steps 1–5 is missing for a resource the scenario needs, `test-plan`
records it as a `blocked_on` entry and halts. `test-creator` never fills the
gap inline — a schema-less resource has nothing for `assert_schema` to check,
and a service-less resource would force a test to reach around the `api/`
layer, which this framework never does.

## Structure of an E2E test

- Each test method gets a **docstring** (never a comment above the method) restating its
  `test_name` with a one-line description, e.g.:
  ```python
  def test_create_then_update_then_delete_user_e2e(self, users_service, cleanup_users):
      """test_create_then_update_then_delete_user_e2e: create a user, verify it via
      GET, update it, then confirm deletion."""
  ```
  There is no separate id scheme — `test_name` is the test's identity, so the docstring exists
  for traceability when grepping generated code or reports, not to introduce a second name.
- Arrange only through existing fixtures (`users_service`, `token_provider`,
  `created_user`, `cleanup_users`, etc. from [tests/conftest.py](../tests/conftest.py))
  and the payload builder under `api/payloads/` (e.g.
  [api/payloads/users_payloads.py](../api/payloads/users_payloads.py))
  — never call `core.http_client` / `core.auth` / `core.config` directly from a
  test.
- Chain calls through the relevant `*Service` class (e.g. `UsersService`), never
  by hand-building requests — one method per business action, same as
  [api/users_service.py](../api/users_service.py). The service must exist
  before the test is written — see "Build order for a new resource" above.
- Every intermediate and final response goes through `core.assertions`
  (`assert_status`, `assert_field`, `assert_fields`, `assert_field_present`,
  `assert_schema`, `assert_list`, `assert_header`/`assert_header_present`,
  `assert_response_time`) — never a bare `assert`. A bare `assert` produces no
  record in the report and is invisible to execution-review.
- Use `soft_assertions()` (from `core.assertions`) when a step of the journey
  should verify several independent things without aborting the rest of that
  step's checks — matching how it's already used elsewhere in the codebase.
- Data created mid-flow must be cleaned up regardless of pass/fail — use
  `cleanup_users` (append the id as soon as it's known) or a fixture-provided
  teardown, never a manual `finally` in the test body. If no existing fixture
  fits, that's a `blocked_on` entry for `test-setup` — never invent one in the
  test.
- Use `build_user()` with an explicit `_seed=` (plus overrides/`OMIT` as needed)
  for payloads — deterministic, reproducible data, never ad hoc random values.
  Note that `build_user()` with no seed always yields the *same* email, so two
  unseeded tests collide; pin a distinct seed per call.
- Apply the marker `plan.md` names (`smoke`, `regression`, or `contract`) — the
  set is fixed by `pytest.ini`.

## Naming

- `test_name`: `test_<verb>_<...>_e2e` describing the journey, e.g.
  `test_create_then_update_then_delete_user_e2e`.
- `file_name`: `test_<feature>_e2e.py`.
- `class_name`: `Test<Feature>E2E` (e.g. `TestUsersE2E` for `tests/users/test_users_e2e.py`).
  Every E2E `test_name` for a given `file_name` shares this same `class_name` — one class per
  file, holding all of that file's E2E test methods.

These are derived the same way every time from the feature/module name and
scenario, per the QA Agent's fixed naming-derivation rule — testcase-writer and
test-creator must not invent alternate forms.

## Traceability

Same rule as the rest of the QA Agent pipeline: the `test_name` docstring on
each test method is how test-review and execution-review match generated E2E
test code back to `testcase.md` and `plan.md`. Every E2E test must carry one.

## What NOT to do

- Don't assert on internal timing/ordering that gorest.in doesn't guarantee.
- Don't skip cleanup because "the last step deletes it anyway" — an assertion
  failure mid-test can abort before that step runs; rely on the
  fixture-provided teardown instead.
- Don't invent new assertion helpers for something `core/assertions.py`
  already covers.
