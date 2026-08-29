---
name: execution-review
description: Reviews a test execution/run report against plan.md and testcase.md across all testcase.md files under testcase_dir, matching by test_name, checking intended coverage/validations were actually exercised and passed. Does not write code.
---

# execution-review

Operates over `testcase_dir` (under `base_dir`): reviews a test execution/run report against `plan.md` and the relevant `testcase.md` file(s), matching by `test_name` across **all** test cases in **all** `testcase.md` files under `testcase_dir` — not just one file or one test case.

## Steps

1. Resolve `testcase_dir` for this session.
2. Enumerate every `testcase.md` file under `testcase_dir` and every `test_name` within each, plus their `plan.md` counterparts.
3. Take the execution/run report supplied by the user (or located per their instructions).
4. For each `test_name`, check:
   - Was it actually exercised in the run?
   - Did it pass/fail, and does that align with `plan.md`'s intended validations/schema_expectations?
   - Any `test_name` in scope missing from the run report entirely?
5. Report findings per `test_name`.

## Boundaries

- Never creates or edits test code or any other repo file — read-only review.
