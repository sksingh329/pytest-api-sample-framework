---
name: test-plan
description: Builds/updates plan.md for every test case across every testcase.md under testCaseBaseDir, resolving each fixture, service, payload, and schema to an exact existing identifier and halting on anything missing. Never writes code.
---

# test-plan

Operates over `testCaseBaseDir`: enumerates **every** `testcase.md` file found
there, and **every** test case within each file, and creates/updates the corresponding `plan.md`.

`plan.md` is one-per-test-case, at `testCaseBaseDir/<feature>/<test_name>/plan.md` — the same
subfolder that holds that `test_name`'s `testcase.md`, named for the `test_name` it plans. Never
grouped into one file per feature — `testcase.md` and `plan.md` use exactly the same
one-per-`test_name` shape, for the same folder, on purpose.

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

## `plan.md` fixed structure — mandatory, from `templates/plan.md.template.md`

One `### <test_name>` section — the single entry in that `test_name`'s own `plan.md`, under a
`# <Feature> -- Plan` H1. Never any other shape — see the template file for the full skeleton plus
a filled example.

```
### <test_name>
status: READY | BLOCKED
marker: smoke | regression | contract
file_name: tests/<feature>/test_<x>.py
class_name: Test<Feature>[<Suffix>]
target: <file_name> :: <class_name> :: <test_name>
fixtures:
  - name: <fixture>   source: tests/conftest.py   status: EXISTS|MISSING
services:
  - ref: api.<x>_service.<X>Service.<method>       status: EXISTS|MISSING
payloads:
  - ref: api.payloads.<x>_payloads.build_<x>   args: <literal>   status: EXISTS|MISSING
schema_expectations:
  - step: <n>   schema_key: "<key>"|none   source: api/schemas/<x>.py|n/a   status: EXISTS|MISSING   reason: <required when schema_key is none>
validations:
  - step: <n>   helper: <core.assertions fn>   args: <literal expected value>   # <optional note>
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

Never reorder, rename, or drop a field when regenerating. `reason` is required whenever
`schema_key` is `none` — say why there's nothing to validate. A validation's trailing `# <note>`
comment is optional but should be used whenever a scenario makes more than one call, so each
check's call is unambiguous.

## Outcome presentation — mandatory

After resolving each `test_name`'s entry, present the outcome to the user in exactly the table
shape in `templates/plan-outcome-presentation.md` — never as prose, never as a raw dump of the
`plan.md` fields. One table per `test_name`, titled `<test_name> → status: READY|BLOCKED`. Fixed
row order: `fixtures`, `services`, `payloads`, `schema_expectations`, `validations`, `cleanup`,
plus `soft_grouping` (only if not `none`), `blocked_on` (only if `BLOCKED`), `open_questions`
(only if non-empty). See that file for the row-by-row guidance and a filled example.

This is a report, not an approval gate — `test-plan` writes `plan.md` itself and does not wait on
the user before writing. The table is how the user sees *why* each row resolved the way it did
without reading the raw file.

## The gate

A `test_name`'s entry is `READY` only when **all** of these hold:

- `test_name`, `class_name`, and `file_name` are all present and non-empty — these identify
  *where the test lives*, and `test-creator` must not start without them
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
across every in-scope `test_name`, grouped by remediation, with a copy-pasteable invocation. A gap
needing a new marker or a `core/` change routes to the user, not to `test-setup` — `pytest.ini`
and `core/` are human-only.

## Filling each field

- **validations** — compose helpers from `core/assertions.py` only. These always exist, so
  validations never block. Pin the literal expected value (status code, field value), not a
  description of it. This is the internal validation-planner step; it writes no code.
- **schema_expectations** — the exact `SCHEMAS` key string passed to `assert_schema`, with
  `source` as its file. A step with no body to validate (a 204, an unmodeled error shape, say)
  records `schema_key: none`, `source: n/a`, and a `reason` explaining why.
- **fixtures** — resolved fixture names from the inventory. Never describe a fixture in prose.
- **data** — an explicit `_seed` per `build_*` call. Note that `build_user()` with no seed always
  yields the *same* email, so two unseeded tests collide; pin distinct seeds.
- **cleanup** — the fixture that tears down anything created. `none` must be a deliberate
  choice, not an omission.
- **marker** — one of the markers in `pytest.ini`. A marker not in `pytest.ini` is a
  `blocked_on` entry with `remediation: human`.
- **step numbers** — number every validation and schema row so a chained id has an unambiguous
  producer and `test-review` can check ordering.
- **file_name, class_name, test_name** — carried verbatim from `testcase.md`, never re-derived
  here. If any is missing from `testcase.md`, that's an `open_questions` entry, not something to
  guess — route back to testcase-writer rather than inventing a value.
- **class_name consistency** — every `test_name` sharing a `file_name` must carry the same
  `class_name`. A mismatch across entries for the same file is a plan defect: stop and ask.

## Source precedence

When sources disagree, resolve in this order:

1. `testcase.md` (confirmed source of test intent)
2. Existing codebase patterns / the inventory
3. Postman collection JSON (if available, via `postmanCollectionPath`)

If a conflict can't be resolved this way, stop and ask the user rather than picking one silently.

For E2E test plans, also consult `.claude/instructions/e2e-agent-instructions.md`.

## Steps

1. Resolve `testCaseBaseDir` and `postmanCollectionPath` for this session (ask if not yet provided).
2. Build the Step 0 inventory.
3. Enumerate every `testcase.md` under `testCaseBaseDir` and every test case within each.
4. For each `test_name`, resolve every fixture, service, payload, and schema against the inventory;
   mark each `EXISTS` or `MISSING`; derive validations from `core/assertions.py`.
5. Set `status` per the gate above and populate `blocked_on` for every `MISSING` row.
6. Write/update `testCaseBaseDir/<feature>/<test_name>/plan.md` for each in-scope `test_name`,
   preserving the fixed structure.
7. Present the outcome table for each `test_name` (see "Outcome presentation" above).
8. If any entry is `BLOCKED`, emit the consolidated halt.
9. If re-invoked on a `test_name` that already has a `plan.md`, overwrite only that `test_name`'s
   file — never touch another `test_name`'s `plan.md`.

## Boundaries

- Never creates or edits repo code of any kind — reads and plans only, writes `plan.md`.
- Never invokes `test-setup` or any other skill.
- Never marks a row `EXISTS` on anything but a literal inventory match.
- Never writes `plan.md` anywhere but `testCaseBaseDir/<feature>/<test_name>/plan.md`.
- Never writes `plan.md` in any shape other than `templates/plan.md.template.md`'s.
- Never touches another `test_name`'s `plan.md` when adding or updating one.
