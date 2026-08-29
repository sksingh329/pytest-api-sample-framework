---
name: testcase-writer
description: Converts an approved test-design output into structured testcase.md, after user confirmation of each test case's fields. test_name is the test's identity — frozen once approved. Does not identify new test cases and does not write code.
---

# testcase-writer

Converts an approved test-design output into structured `testcase.md`. Producing `testcase.md` is
this skill's sole output — it does not identify new test cases (that's test-design's job) and does
not write code.

`testcase.md` is consumed by test-plan, test-creator, test-review, and execution-review, and can
contain multiple test cases in a single file.

## Steps

1. Resolve `testcase_dir` for this session (ask if not yet provided).
2. Take the approved test-design output (from `test_design_dir`, or as given directly by the user).
3. Read the existing inventory of `test_name`s across every `testcase.md` under `testcase_dir` —
   a new `test_name` must not collide with one already assigned.
4. For each test case, derive and present these fields to the user for explicit approval before
   writing anything:
   - `test_name` — this is the test's identity (see the rule below); get it right here
   - `file_name` (full path, e.g. `tests/users/test_users_e2e.py`)
   - `class_name` — every test belongs to a class; there are no standalone test functions in
     pipeline-generated code (see "Class grouping" below). Required, never `n/a`.
   - `test steps` (including `setup`, if needed)
   - `assertion`
   - `marker` — one of the markers declared in `pytest.ini` (`smoke`, `regression`, `contract`)
5. Never assume a fixture, setup step, or assertion not explicitly given or clearly established in
   existing codebase patterns — ask the user.
6. Derive `file_name`, `class_name`, and `test_name` consistently from the feature/module name and
   scenario, matching existing codebase casing conventions.
7. Incorporate any corrections the user requests and reconfirm before finalizing — this
   confirmation is the last chance to change `test_name`; see the rule below.
8. Only after confirmation, write/update `testcase.md` under `testcase_dir`.
9. For E2E scenarios, follow the structure/conventions in
   `.claude/instructions/e2e-agent-instructions.md` rather than inventing new ones.

## `test_name` rule — identity, frozen after approval

There is no separate `test_id`: `test_name` **is** the identity carried through the rest of the
pipeline. Once approved in step 7, it is frozen — it must be carried unchanged into `plan.md`, the
generated test method's name, that method's docstring, `test-review` output, and
`execution-review` output.

`test_name` never changes after approval, even for a typo or clarity fix. A genuine rename is a
delete-and-recreate — retire the old entry (and its downstream `plan.md`/code/review history) and
create a new one with a new `test_name` — never an in-place edit. This is why step 3's collision
check and step 7's last-chance confirmation matter: get it right before it's frozen.

## Class grouping

Every test belongs to a class — `class_name` is required, never `n/a`, and there are no
standalone test functions in pipeline-generated code (`test-creator` never writes one outside a
class). All test cases that share a `file_name` must share the same `class_name` — one class per
file, not one class per test. Derive `class_name` as `Test<PascalCase(feature)>` for a file's
primary class (e.g. `TestUsers` for `tests/users/test_users.py`), or
`Test<PascalCase(feature)><PascalCase(suffix)>` when the file name carries a suffix (e.g.
`TestUsersE2E` for `tests/users/test_users_e2e.py`, `TestUsersAuth` for
`tests/users/test_users_auth.py`).

Before assigning a new `class_name`, check whether the target `file_name` already has test cases
in `testcase_dir` — if it does, reuse their `class_name` rather than deriving a new one; a
mismatch would split one file's tests across two classes.

## Idempotency

If `testcase.md` already exists and this skill is re-invoked (e.g. adding 2 more cases to a file
that already has 5), append/update only the new or changed entries — leave existing, unaffected
entries untouched. Never regenerate the whole file from scratch.

## Boundaries

- Never creates or edits test code or any other repo file.
- Never invents new test cases beyond what test-design (or the user) approved.
- Never assigns a `test_name` that collides with an existing one under `testcase_dir`.
