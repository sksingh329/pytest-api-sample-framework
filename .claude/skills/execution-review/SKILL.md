---
name: execution-review
description: Runs the newly created test(s) via pytest, then validates the resulting report and plan.md/testcase.md alignment across all in-scope test_names under testCaseBaseDir, writing one execution-report.md per test_name. Executes tests but never writes test code, plan.md, or testcase.md.
---

# execution-review

Operates over `testCaseBaseDir`: for each in-scope `test_name`, **runs its test via pytest**,
then reviews the resulting evidence against that `test_name`'s `plan.md`
(`testCaseBaseDir/<feature>/<test_name>/plan.md`) and its `testcase.md` entry — matching by
`test_name` across **all** test cases in **all** `testcase.md` files under `testCaseBaseDir`, not
just one file or one test case. The outcome of that review is written to
`testCaseBaseDir/<feature>/<test_name>/execution-report.md` — the same subfolder that already
holds that `test_name`'s `testcase.md` and `plan.md`.

This is the only skill that executes pytest. It still never writes test code, `plan.md`, or
`testcase.md` — running a test is not editing one; `execution-report.md` is a new file, not an
edit to either of those.

## Scope

- If the user names specific test case(s) or a feature ("the test I just created," "the users
  feature"), run only those.
- If nothing is named, run every in-scope `test_name` whose `plan.md` reads `status: READY` —
  never a `BLOCKED` entry; there's nothing to execute if `test-creator` hasn't produced code for
  it. If any named test_name is `BLOCKED`, say so and stop for that one rather than running
  nothing at all.

## Steps

1. Resolve `testCaseBaseDir` for this session.
2. Enumerate every `testcase.md` file under `testCaseBaseDir` and every `test_name` within each,
   plus each one's own `plan.md` (`testCaseBaseDir/<feature>/<test_name>/plan.md`).
3. Determine scope per "Scope" above.
4. For each in-scope `test_name`, read its `plan.md` `target` (`file_name :: class_name ::
   test_name`) and run it precisely:
   `pytest <file_name>::<class_name>::<test_name>` — e.g.
   `pytest tests/users/test_users.py::TestUsers::test_delete_user`. Group multiple targets from
   the same run into one `pytest` invocation rather than one process per test, unless the user
   asked for isolation.
   - Default environment is `api_env=dev` (the repo's `pytest.ini` default) unless the user
     names a different one — pass it as `API_ENV=<env> pytest ...`, never edit `pytest.ini`.
   - Never edit `.env`, `environments.py`, or any `core/**` file to make a run pass — those are
     human-only; a run that fails because of them gets reported, not worked around.
5. Locate that run's evidence: `reports/<api_env>/<timestamp>/report.html` and `summary.json`
   (per `docs/CLAUDE.md`), and the per-worker ledger under `reports/<api_env>/ledger/` when
   assertion-level detail is needed beyond pass/fail.
6. For each `test_name`, cross-check the evidence against its `plan.md` and `testcase.md`:
   - Did it collect and run at all (not skipped, not a collection error)?
   - Did it pass/fail, and does that align with what `plan.md`'s `validations` and
     `schema_expectations` describe should be checked?
   - Does the run's `@pytest.mark.*` match the `marker` `plan.md` pinned?
   - Does the outcome match `testcase.md`'s original `Setup`/`Act`/`Assert` intent?
   - Any in-scope `test_name` that didn't get run at all (e.g. a collection failure meant it
     never reached the report)?
7. Flag anything the run reveals that's wrong in `plan.md` itself, not just in the code — e.g. a
   fixture `plan.md` marked `EXISTS` that pytest reports as a fixture error, or a
   `file_name`/`class_name` mismatch against where the test actually collected. This is a plan
   defect: report it and route back to `test-plan`, don't silently note it as a test failure.
8. Report findings per `test_name`, referencing the report path and file/line where possible.
9. Write `testCaseBaseDir/<feature>/<test_name>/execution-report.md` for each in-scope
   `test_name` (see "Write format" below) — the same content just reported, captured as a durable
   artifact next to that `test_name`'s `testcase.md` and `plan.md`.

## Write format — mandatory

`execution-report.md` is written in the exact shape of
`templates/execution-report.md.template.md` — never any other structure: `run_at`, `target`,
`command`, `outcome`, `marker_match`, `report_path`, `summary_path`, then the **Validations
checked** / **Schema checked** rows (copied from `plan.md`'s own step numbers, each marked
`matched: yes|no` against what the evidence showed), an **Intent alignment** line against
`testcase.md`'s Setup/Act/Assert, and a **Findings** list (`none` only when the run is clean
end-to-end) — each finding tagged with where it routes (`test-creator` | `test-plan` | `none`).

One file, one `## <test_name>` section, same one-per-`test_name` shape as `testcase.md` and
`plan.md`. Re-running `execution-review` for a `test_name` that already has a report overwrites
that file in place with the latest run — it holds the most recent execution, not a history.

## Boundaries

- Runs pytest — the only skill in this pipeline that executes tests.
- Never creates or edits test code, `plan.md`, or `testcase.md` — running a test is not writing
  one; findings route back to the owning skill (`test-creator`, `test-plan`, or the user).
- Writes only `testCaseBaseDir/<feature>/<test_name>/execution-report.md` — no other repo file.
- Never writes `execution-report.md` in any shape other than
  `templates/execution-report.md.template.md`'s.
- Never touches another `test_name`'s `execution-report.md` when writing one.
- Never edits `pytest.ini`, `.env`, `environments.py`, or any `core/**` file to make a run pass.
- Never runs a `BLOCKED` `test_name`'s test — there's no code for it yet.
