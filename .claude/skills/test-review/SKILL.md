---
name: test-review
description: Reviews generated test code against plan.md and testcase.md by test_name — first a mechanical conformance pass, then a judgement pass for deviations, gaps, and missing coverage. Writes nothing.
---

# test-review

Reviews the test code created by `test-creator` against `plan.md` (and `testcase.md` for original
intent), matching by `test_name`. Two passes, in order: mechanical first, judgement second.

## Steps

1. Resolve `testCaseBaseDir` for this session.
2. For each `test_name` in scope, locate the `testcase.md` entry, the `plan.md` entry, and the
   generated test code (matched via the `test_name` docstring left by `test-creator`).
3. Run the mechanical pass, then the judgement pass.
4. Report findings per `test_name`, referencing file/line where possible.

## Pass 1 — mechanical conformance

Each of these is a yes/no check, not a judgement call. Extract from the generated test: the class
it's a method of, the fixture parameters of the `def` (after `self`), every service-method call,
every `assert_*` call and its literal schema key, the applied `@pytest.mark.*`, and the method's
docstring.

- **Class grouping** — the method's `class_name` matches `plan.md`, and it's a method (`self` as
  first param) inside that class, never a standalone function. Every `test_name` sharing a
  `file_name` lives in the *same* class — a second class for the same file is a violation.
- **Fixtures match both ways** — every fixture used appears in the plan's `fixtures` (an extra is
  a *deviation*), and every planned fixture is used (an unused one is *plan drift*).
- **Schema keys** — every `assert_schema` key literal appears in the plan's `schema_expectations`.
- **Assertion helpers** — every `assert_*` used exists in `core/assertions.py` *and* appears in
  the plan's `validations`.
- **Marker** — matches the plan's `marker` exactly.
- **No bare `assert`** — zero bare `assert` statements. A bare assert produces no report record
  and is invisible to `execution-review`.
- **No layer violations** — no `core.http_client`, `core.auth`, `core.config`, or `requests`
  import in a test file; tests reach the API only through a service fixture.
- **Write scope** — every file touched by the run is under `tests/<feature>/test_*.py`. A change
  to `tests/conftest.py` or `api/**` from `test-creator` is a scope violation, reported as such.
- **Cleanup** — the plan's `cleanup` fixture is wired; no inline `try/finally` teardown.
- **Traceability** — every test carries a docstring restating its `test_name`. A comment above
  the method instead of a docstring is a conformance failure, not a stylistic variant.

## Pass 2 — judgement

Compare the code against `plan.md`'s `validations` and `schema_expectations` and against
`testcase.md`'s original intent (`Setup`, `Act`, `Assert`), and flag:

- **Deviations** — code does something the plan/testcase didn't call for.
- **Gaps** — plan/testcase requirements not exercised in the code.
- **Missing coverage** — `test_name`s in `testcase.md`/`plan.md` with no corresponding code.
- **Step ordering** — for E2E, the chained steps run in the plan's `step` order and each chained
  value has the producer the plan names.

## Boundaries

- Never creates or edits any repo file — read-only review.
- Never fixes what it finds; it reports, and the fix routes back to the owning skill
  (`test-creator` for test code, `test-setup` for a missing building block, `test-plan` for a
  plan defect).
