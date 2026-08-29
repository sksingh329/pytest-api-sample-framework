---
name: test-pipeline
description: Orchestrates the full QA Agent pipeline end to end — testcase-writer (if no testcase.md exists yet), test-plan, test-setup if anything is BLOCKED (pausing for its mandatory approval), test-creator, test-review, and execution-review — over the test cases in scope.
---

# test-pipeline

Orchestrator skill that, for the test cases in scope under `testCaseBaseDir`, runs the full chain
from design to execution, passing output forward at every stage:

0. **testcase-writer**, only if the scope has no `testcase.md` yet → produces `testcase.md`,
   pausing for its own mandatory approval
1. **test-plan** → produces/updates `plan.md`
2. **test-setup**, only if anything is `BLOCKED` → fills the gap, pausing for its own mandatory
   approval, then hands back to test-plan
3. **test-creator** → produces test code, only from `READY` entries
4. **test-review** → reviews the generated test code against `plan.md`
5. **execution-review** → runs the generated test(s) via pytest and writes
   `execution-report.md`

Every one of these still owns its own file per
`.claude/prompts/skill-creation-master-prompts.md`'s ownership table — `test-pipeline` writes
nothing itself at any stage; it only sequences the calls and re-checks state between them.

## Steps

1. Resolve `testCaseBaseDir` for this session (ask if not yet provided).
2. Confirm scope with the user: which feature/request, or which existing `testcase.md`
   file(s)/`test_name`(s), are in scope.
3. **Design gate.** Check whether `testcase.md` already exists for every `test_name` in scope
   (`testCaseBaseDir/<feature>/<test_name>/testcase.md`).
   - If it already exists for all of them, continue to step 4.
   - If any are missing, invoke `testcase-writer` for the scope's request. Its own mandatory
     approval step still applies in full — it presents the derived fields and stops for explicit
     confirmation before writing `testcase.md`. This pipeline does not shortcut that approval.
     Once `testcase-writer` finishes, continue to step 4 with the resulting `test_name`(s) added
     to scope.
4. Invoke `test-plan` for the full in-scope set.
5. **Plan gate.** Check every in-scope `test_name`. Treat any inconsistency between `status`,
   `blocked_on`, and the per-row statuses as `BLOCKED` — fail closed.
   - If every entry is `READY`, continue to step 7.
   - If any entry is `BLOCKED`, go to step 6.
   - If any entry has non-empty `open_questions` (an ambiguity `test-setup` can't resolve — it
     only builds missing building blocks), halt entirely and hand control back to the user; do
     not invoke `test-setup` for this.
6. **Remediate.** Invoke `test-setup` against the aggregated `blocked_on` list. `test-setup`'s own
   Approve phase still applies in full — it presents the exact proposed code and stops for
   explicit user confirmation before writing anything. This pipeline does not shortcut that
   approval; chaining into `test-setup` does not make its write silent. Once `test-setup`
   finishes, return to step 4 — `test-plan` must run again so every status is recomputed against
   the new inventory. Never carry forward statuses from before a `test-setup` run.
7. Invoke `test-creator` using the `READY` entries.
8. Invoke `test-review` against the generated code and `plan.md`.
9. Invoke `execution-review` for the same in-scope `test_name`(s) — it runs each one via pytest
   (default `api_env=dev` unless the user named another) and writes that `test_name`'s
   `execution-report.md`. State the environment being hit in the summary; invoking
   `test-pipeline` is itself the user's trigger to execute, so this step is not gated behind a
   second confirmation — but a request that explicitly asked to stop short of running the tests
   (e.g. "just generate the code, don't run it") skips this step.
10. Summarize the end-to-end result: scenarios written (if `testcase-writer` ran), plan produced,
    any setup performed, code generated, review findings, and the execution outcome —
    referencing each `execution-report.md` path.

## Boundaries

- Writes nothing itself.
- The `testcase-writer` step writes only `testCaseBaseDir/<feature>/<test_name>/testcase.md`, and
  only after its own mandatory approval — this pipeline never bypasses that approval, and never
  invokes it when `testcase.md` already exists for the scope (that would be an edit, not a
  design step, and `testcase-writer` doesn't do those either).
- The `test-setup` step writes only within its own scope (`api/constants.py`,
  `api/<x>_service.py`, `api/payloads/<x>_payloads.py`, `api/schemas/<x>.py`,
  `tests/conftest.py`) and only after its own mandatory approval — this pipeline never bypasses
  that approval.
- The `test-creator` step writes code, and only `tests/<feature>/test_*.py` — never
  `tests/conftest.py`, never `api/**`, never the framework's core/engine layer.
- The `execution-review` step writes only `testCaseBaseDir/<feature>/<test_name>/
  execution-report.md` — never edits `plan.md`, `testcase.md`, or test code, and never edits
  `pytest.ini`/`.env`/`environments.py`/any `core/**` file to make a run pass.
- Halts entirely (does not invoke `test-setup`) on `open_questions` — those need a human answer,
  not a scaffolded building block, at either the design stage or the plan stage.
- Never runs a `BLOCKED` `test_name`'s test at the execution-review stage — there's no code for
  it yet; a `BLOCKED` entry that reached step 10 is itself a pipeline defect, not expected state.
