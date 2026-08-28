---
name: test-pipeline
description: Runs test-plan, then test-creator, then test-review in sequence over the test cases in scope, halting if any test_id is BLOCKED. Never auto-invokes test-setup.
---

# test-pipeline

Orchestrator skill that, for the test cases in scope under `testcase_dir` (under `base_dir`),
runs the following in sequence, passing output forward:

1. **test-plan** → produces/updates `plan.md`
2. **test-creator** → produces test code, only from `READY` entries
3. **test-review** → reviews the generated test code against `plan.md`

## Steps

1. Resolve `testcase_dir` for this session (ask if not yet provided).
2. Confirm scope with the user: which `testcase.md` file(s) / `test_id`(s) are in scope.
3. Invoke `test-plan` for that scope.
4. **Gate.** Proceed only if every in-scope `test_id` has `status: READY`. If any is `BLOCKED`,
   or if `open_questions` is non-empty, halt: report the aggregated gaps grouped by remediation,
   and hand control back to the user. Treat any inconsistency between `status`, `blocked_on`, and
   the per-row statuses as `BLOCKED` — fail closed.
5. Invoke `test-creator` using the `READY` entries.
6. Invoke `test-review` against the generated code and `plan.md`.
7. Summarize the end-to-end result (plan produced, code generated, review findings).

## Halting and re-entry

`test-setup` is **not part of this pipeline and is never auto-invoked.** When the gate halts,
the pipeline stops and the user decides — it does not "helpfully" chain into building the missing
fixture, schema, service, payload builder, or endpoint.

After the user runs `test-setup`, re-enter at step 3, not step 5: `test-plan` must run again so
every status is recomputed against the new inventory. Never carry forward statuses from before a
`test-setup` run.

## Boundaries

- Writes nothing itself.
- Only the `test-creator` step writes code, and only `tests/<feature>/test_*.py` — never
  `tests/conftest.py`, never `api/**`, never the framework's core/engine layer.
- Never auto-invokes `test-setup`.
- Does not run the tests, and does not include `execution-review` — those are separate,
  user-triggered steps.
