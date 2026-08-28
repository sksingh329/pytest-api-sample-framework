---
name: test-plan
description: Builds/updates plan.md for every test case across every testcase.md under testcase_dir, resolving each fixture, service, payload, and schema to an exact existing identifier and halting on anything missing. Never writes code.
---

# test-plan

Operates over `testcase_dir` (under `base_dir`): enumerates **every** `testcase.md` file found
there, and **every** test case within each file, and creates/updates the corresponding `plan.md`.

`plan.md` does not describe what a test needs — it **names** what already exists, by exact
identifier, with a status. Anything missing halts the pipeline instead of being invented.

## Step 0 — inventory (mandatory, before planning anything)

Read the repo and build the inventory of available building blocks. Do this once per invocation.

| Inventory | Source |
|---|---|
| fixtures | `tests/conftest.py`, `tests/**/conftest.py`, root `conftest.py` — every `@pytest.fixture` def, with scope |
| schema keys | `api/schemas/**/*.py` (excl. `__init__.py`) — the literal keys of each module's `SCHEMAS` dict |
| services | `api/*_service.py` — public methods of each `BaseService` subclass |
| endpoints | `api/constants.py` — `*Endpoints` classes and their attributes |
| payload builders | `api/payloads/*.py` — `build_*` functions |
| assertion helpers | `core/assertions.py` — public `assert_*` names + `soft_assertions` |
| markers | the `markers =` block of `pytest.ini` |

**A row is `EXISTS` only on a literal string match against this inventory.** "A similar fixture
exists so it will probably work" is `MISSING`. No fuzzy matching, no near-enough.

## `plan.md` fixed structure

One entry per `test_id`:

```
### <test_id>
status: READY | BLOCKED
marker: smoke | regression | contract
target: tests/<feature>/test_<x>.py :: <test_name>
fixtures:
  - name: <fixture>   source: tests/conftest.py   status: EXISTS|MISSING
services:
  - ref: api.<x>_service.<X>Service.<method>       status: EXISTS|MISSING
payloads:
  - ref: api.payloads.<x>_payloads.build_<x>   args: <literal>   status: EXISTS|MISSING
schema_expectations:
  - step: <n>   schema_key: "<key>"   source: api/schemas/<x>.py   status: EXISTS|MISSING
validations:
  - step: <n>   helper: <core.assertions fn>   args: <literal expected value>
data: <explicit _seed per build_* call, or fixed literals>
cleanup: <fixture name> | none
soft_grouping: <steps wrapped in soft_assertions(), or none>
blocked_on:
  - kind: fixture|schema|service|payload|endpoint|marker
    identifier: <exact name that must be created>
    required_by: <step>
    remediation: invoke test-setup | human
open_questions: []
```

Never reorder, rename, or drop a field when regenerating.

## The gate

A `test_id` is `READY` only when **all** of these hold:

- `blocked_on` is empty
- `open_questions` is empty
- every row reads `EXISTS`

These three are redundant on purpose. If they ever disagree, the entry is `BLOCKED` — fail
closed, never `READY`.

`open_questions` and `blocked_on` mean different things and must not be conflated:

- `open_questions` — "I need an answer from you" (an ambiguous expectation, an undecided value).
- `blocked_on` — "a building block must be built before this test can exist."

## Halting

`test-plan` never invokes `test-setup` and never creates a missing fixture, schema, service,
payload builder, or endpoint. When gaps exist, emit **one consolidated halt** listing every gap
across every in-scope `test_id`, grouped by remediation, with a copy-pasteable invocation. A gap
needing a new marker or a `core/` change routes to the user, not to `test-setup` — `pytest.ini`
and `core/` are human-only.

## Filling each field

- **validations** — compose helpers from `core/assertions.py` only. These always exist, so
  validations never block. Pin the literal expected value (status code, field value), not a
  description of it. This is the internal validation-planner step; it writes no code.
- **schema_expectations** — the exact `SCHEMAS` key string passed to `assert_schema`. A step with
  no body to validate (a 204, say) records `schema_key: none` with a reason.
- **fixtures** — resolved fixture names from the inventory. Never describe a fixture in prose.
- **data** — an explicit `_seed` per `build_*` call. Note that `build_user()` with no seed always
  yields the *same* email, so two unseeded tests collide; pin distinct seeds.
- **cleanup** — the fixture that tears down anything created. `none` must be a deliberate
  choice, not an omission.
- **marker** — one of the markers in `pytest.ini`. A marker not in `pytest.ini` is a
  `blocked_on` entry with `remediation: human`.
- **step numbers** — number every validation and schema row so a chained id has an unambiguous
  producer and `test-review` can check ordering.

## Source precedence

When sources disagree, resolve in this order:

1. `testcase.md` (confirmed source of test intent)
2. Existing codebase patterns / the inventory
3. Postman collection JSON (if available, via `postman_collection_path`)

If a conflict can't be resolved this way, stop and ask the user rather than picking one silently.

For E2E test plans, also consult `docs/e2e-agent-instructions.md`.

## Steps

1. Resolve `testcase_dir` and `postman_collection_path` for this session (ask if not yet provided).
2. Build the Step 0 inventory.
3. Enumerate every `testcase.md` under `testcase_dir` and every test case within each.
4. For each `test_id`, resolve every fixture, service, payload, and schema against the inventory;
   mark each `EXISTS` or `MISSING`; derive validations from `core/assertions.py`.
5. Set `status` per the gate above and populate `blocked_on` for every `MISSING` row.
6. Write/update `plan.md`, preserving the fixed structure.
7. If any entry is `BLOCKED`, emit the consolidated halt.
8. If re-invoked on an existing `plan.md`, update only new/changed `test_id` entries — don't
   regenerate the whole file.

## Boundaries

- Never creates or edits repo code of any kind — reads and plans only, writes `plan.md`.
- Never invokes `test-setup` or any other skill.
- Never marks a row `EXISTS` on anything but a literal inventory match.
