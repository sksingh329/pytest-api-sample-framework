---
name: test-creator
description: Writes test files from a READY plan.md, composing only building blocks the plan resolved to existing identifiers. Writes tests/<feature>/test_*.py and nothing else.
---

# test-creator

Creates automated test code strictly from `plan.md`. Does not re-derive requirements from the
original user request or `testcase.md` directly — `plan.md` is the single source of truth at this
stage.

Its job is **wiring, not invention**: it composes fixtures, service methods, payload builders,
schema keys, and assertion helpers that `plan.md` already resolved to real identifiers.

## Write scope

Writes only `tests/<feature>/test_*.py`.

Never `tests/conftest.py`, never `api/**`, never `core/**`, never `pytest.ini`. Those belong to
`test-setup` (or to the user). If something is missing, this skill stops — it never fills the gap
itself.

## Preconditions

- `plan.md` exists, and every in-scope `test_id` has `status: READY` — meaning `blocked_on`
  empty, `open_questions` empty, and every row `EXISTS`.
- Any `BLOCKED` entry: **write nothing**, print that entry's `blocked_on` list, and tell the user
  to invoke `test-setup` (or to make the human-only change). Do not partially generate.
- Before writing, re-verify each `EXISTS` row against the live repo with a quick grep. `plan.md`
  may be stale if the repo changed after it was written; trust the repo, not the plan.

## Closed-world rule

The generated test may reference **only** the identifiers listed in that `test_id`'s `fixtures`,
`services`, `payloads`, `schema_expectations`, and `validations` rows.

This applies to *external references only* — fixtures, service methods, payload builders, schema
keys, assertion helpers, markers. Ordinary Python inside the test body stays free: locals, loops,
and chained values like `created_id = response.json()["id"]` are expected and need no plan entry.

If the code would need any external reference the plan didn't list, that is a **plan defect**:
stop, say what's missing, and route back to `test-plan`. Never add it, and never ask the user for
permission to add it inline — a yes in chat is exactly the non-deterministic path this design
removes.

## Steps

1. Resolve `testcase_dir` / `plan.md` location for this session.
2. Check the gate. Any `BLOCKED` in scope → stop as described above.
3. For each `READY` `test_id`, read its plan entry, and `testcase.md` only for naming.
4. Re-verify each `EXISTS` identifier against the repo.
5. Generate the test at the plan's `target` path, composing only listed identifiers:
   - apply the plan's `marker` verbatim
   - use the plan's `data` seeds verbatim — fixed and reproducible, never randomized
   - wrap the steps the plan's `soft_grouping` names in `soft_assertions()`
   - wire the plan's `cleanup` fixture; never write an inline `try/finally` teardown
   - assert only through `core/assertions.py` — a bare `assert` produces no report record and is
     invisible to `execution-review`
6. Reference the `test_id` in a comment (not a docstring) above each test.
7. Use `file_name` / `test_name` exactly as given — don't reinvent. `class_name` is `n/a` in this
   repo; generate plain `test_*` functions, no test classes.

## Boundaries

- Writes only `tests/<feature>/test_*.py`. Every other file has a different owning skill.
- Never touches the framework's core/engine layer (config, HTTP client, assertions, recording,
  reporting) — those are human-only.
- Never creates a fixture, schema, service, payload builder, or endpoint. That's `test-setup`.
- Never modifies `testcase.md` or `plan.md`.
