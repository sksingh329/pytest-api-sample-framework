---
name: testcase-writer
description: Converts an approved test-design output into structured testcase.md, after user confirmation of each test case's fields. Does not identify new test cases and does not write code.
---

# testcase-writer

Converts an approved test-design output into structured `testcase.md`. Producing `testcase.md` is this skill's sole output — it does not identify new test cases (that's test-design's job) and does not write code.

`testcase.md` is consumed by test-plan, test-creator, test-review, and execution-review, and can contain multiple test cases in a single file.

## Steps

1. Resolve `testcase_dir` for this session (ask if not yet provided).
2. Take the approved test-design output (from `test_design_dir`, or as given directly by the user).
3. For each test case, derive and present these fields to the user for explicit approval before writing anything:
   - `test_id` (assigned here — stable, never changes after this point)
   - `test_name`
   - `file_name` (full path, e.g. `tests/users/test_users_e2e.py`)
   - `class_name` — always `n/a`: this repo has no test classes, only plain `test_*` functions.
     Never fill it with a name; a value here propagates into generated code.
   - `test steps` (including `setup`, if needed)
   - `assertion`
   - `marker` — one of the markers declared in `pytest.ini` (`smoke`, `regression`, `contract`)
4. Never assume a fixture, setup step, or assertion not explicitly given or clearly established in existing codebase patterns — ask the user.
5. Derive `file_name`, `class_name`, `test_name` consistently from the feature/module name and scenario, matching existing codebase casing conventions.
6. Incorporate any corrections the user requests and reconfirm before finalizing.
7. Only after confirmation, write/update `testcase.md` under `testcase_dir`.
8. For E2E scenarios, follow the structure/conventions in `docs/e2e-agent-instructions.md` rather than inventing new ones.

## `test_id` rule

`test_id` is assigned once, here, and never changes afterward (even if `test_name` is later edited). It must be carried through unchanged into `plan.md`, generated test code, test-review output, and execution-review output.

## Idempotency

If `testcase.md` already exists and this skill is re-invoked (e.g. adding 2 more cases to a file that already has 5), append/update only the new or changed entries — leave existing, unaffected entries untouched. Never regenerate the whole file from scratch.

## Boundaries

- Never creates or edits test code or any other repo file.
- Never invents new test cases beyond what test-design (or the user) approved.
