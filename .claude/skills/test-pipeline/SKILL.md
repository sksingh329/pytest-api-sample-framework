---
name: test-pipeline
description: Runs test-plan, then test-setup if anything is BLOCKED (pausing for its mandatory approval), then test-creator and test-review, over the test cases in scope.
---

# test-pipeline

Orchestrator skill that, for the test cases in scope under `testCaseBaseDir`,
runs the following in sequence, passing output forward:

1. **test-plan** → produces/updates `plan.md`
2. **test-setup**, only if anything is `BLOCKED` → fills the gap, pausing for its own mandatory
   approval, then hands back to test-plan
3. **test-creator** → produces test code, only from `READY` entries
4. **test-review** → reviews the generated test code against `plan.md`

## Steps

1. Resolve `testCaseBaseDir` for this session (ask if not yet provided).
2. Confirm scope with the user: which `testcase.md` file(s) / `test_name`(s) are in scope.
3. Invoke `test-plan` for that scope.
4. **Gate.** Check every in-scope `test_name`. Treat any inconsistency between `status`,
   `blocked_on`, and the per-row statuses as `BLOCKED` — fail closed.
   - If every entry is `READY`, continue to step 6.
   - If any entry is `BLOCKED`, go to step 5.
   - If any entry has non-empty `open_questions` (an ambiguity `test-setup` can't resolve — it
     only builds missing building blocks), halt entirely and hand control back to the user; do
     not invoke `test-setup` for this.
5. **Remediate.** Invoke `test-setup` against the aggregated `blocked_on` list. `test-setup`'s own
   Approve phase still applies in full — it presents the exact proposed code and stops for
   explicit user confirmation before writing anything. This pipeline does not shortcut that
   approval; chaining into `test-setup` does not make its write silent. Once `test-setup`
   finishes, return to step 3 — `test-plan` must run again so every status is recomputed against
   the new inventory. Never carry forward statuses from before a `test-setup` run.
6. Invoke `test-creator` using the `READY` entries.
7. Invoke `test-review` against the generated code and `plan.md`.
8. Summarize the end-to-end result (plan produced, any setup performed, code generated, review
   findings).

## Boundaries

- Writes nothing itself.
- The `test-setup` step writes only within its own scope (`api/constants.py`,
  `api/<x>_service.py`, `api/payloads/<x>_payloads.py`, `api/schemas/<x>.py`,
  `tests/conftest.py`) and only after its own mandatory approval — this pipeline never bypasses
  that approval.
- The `test-creator` step writes code, and only `tests/<feature>/test_*.py` — never
  `tests/conftest.py`, never `api/**`, never the framework's core/engine layer.
- Halts entirely (does not invoke `test-setup`) on `open_questions` — those need a human answer,
  not a scaffolded building block.
- Does not run the tests, and does not include `execution-review` — those are separate,
  user-triggered steps.
