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

- `plan.md` exists, and every in-scope `test_name` has `status: READY` — meaning `test_name`,
  `class_name`, and `file_name` are all present, `blocked_on` empty, `open_questions` empty, and
  every row `EXISTS`.
- Any `BLOCKED` entry: **write nothing**, print that entry's `blocked_on` list, and tell the user
  to invoke `test-setup` (or to make the human-only change). Do not partially generate.
- Before writing, re-verify each `EXISTS` row against the live repo with a quick grep. `plan.md`
  may be stale if the repo changed after it was written; trust the repo, not the plan.

## Closed-world rule

The generated test may reference **only** the identifiers listed in that `test_name`'s `fixtures`,
`services`, `payloads`, `schema_expectations`, and `validations` rows.

This applies to *external references only* — fixtures, service methods, payload builders, schema
keys, assertion helpers, markers. Ordinary Python inside the test body stays free: locals, loops,
and chained values like `created_id = response.json()["id"]` are expected and need no plan entry.

If the code would need any external reference the plan didn't list, that is a **plan defect**:
stop, say what's missing, and route back to `test-plan`. Never add it, and never ask the user for
permission to add it inline — a yes in chat is exactly the non-deterministic path this design
removes.

## Class grouping

Every generated test is a method inside a class — there are no standalone `test_*` functions in
pipeline-generated code. All `test_name`s that share a `file_name` share a `class_name` and go
into the **same** class in that file; don't split one file's tests across multiple classes and
don't create a new class for each method.

- Method signature: `def <test_name>(self, <fixtures...>):` — `self` first, then the plan's
  `fixtures` in the order listed. Standard pytest class-based fixture injection; no
  `unittest.TestCase` base, no `__init__`.
- If the target file already has the class (from an earlier run against the same `file_name`),
  **add the method to the existing class** — never create a second class with the same name, and
  never duplicate the class declaration.
- If `plan.md`'s `class_name` for this entry doesn't match the class already present in
  `file_name` for other methods, that's a plan defect: stop, don't write, route back to
  `test-plan`.

## Steps

1. Resolve `testcase_dir` / `plan.md` location for this session.
2. Check the gate. Any `BLOCKED` in scope → stop as described above.
3. For each `READY` `test_name`, read its plan entry (`file_name`, `class_name`, `test_name`
   included) — `testcase.md` is consulted only if a plan field is ambiguous, never to override it.
4. Re-verify each `EXISTS` identifier against the repo.
5. Generate the test method inside its `class_name` in `file_name`, per "Class grouping" above,
   composing only listed identifiers:
   - apply the plan's `marker` verbatim
   - use the plan's `data` seeds verbatim — fixed and reproducible, never randomized
   - wrap the steps the plan's `soft_grouping` names in `soft_assertions()`
   - wire the plan's `cleanup` fixture; never write an inline `try/finally` teardown
   - assert only through `core/assertions.py` — a bare `assert` produces no report record and is
     invisible to `execution-review`
6. Give the method a **docstring** restating `test_name` plus a one-line description — this is the
   only place traceability is recorded; **never** a comment above the method for this purpose.
7. Use `file_name` / `class_name` / `test_name` exactly as given in `plan.md` — don't reinvent.

## Boundaries

- Writes only `tests/<feature>/test_*.py`. Every other file has a different owning skill.
- Never touches the framework's core/engine layer (config, HTTP client, assertions, recording,
  reporting) — those are human-only.
- Never creates a fixture, schema, service, payload builder, or endpoint. That's `test-setup`.
- Never modifies `testcase.md` or `plan.md`.
