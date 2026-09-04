<!--
Write template — execution-review

This is the ONLY format execution-report.md is written in. One file per
test case, at testCaseBaseDir/<feature>/<test_name>/execution-report.md —
the same subfolder that already holds that test_name's testcase.md and
plan.md. Never grouped into one file per feature, never a different shape.

Re-running execution-review for a test_name that already has a report:
overwrite that file in place with the latest run's outcome — it only ever
holds this one test_name's most recent execution, not a history.

Field notes:
- validations/schema_checked rows are copied from plan.md's own step
  numbers, each marked matched: yes|no against what the evidence actually
  showed — a status/field mismatch or a check that never fired is `no`.
- findings is empty only when the run is clean end-to-end: collected, ran,
  outcome matched plan.md, every row matched. Anything else is a finding,
  each tagged with where it routes (test-creator | test-plan | none — a
  genuine flake to re-run).
-->

# <Feature> -- Execution Report

## <test_name>

- **run_at**: `<ISO 8601 timestamp>`
- **target**: `<file_name> :: <class_name> :: <test_name>`
- **command**: `<exact pytest invocation, incl. API_ENV if non-default>`
- **outcome**: pass | fail | skip | not_run
- **marker_match**: yes | no
- **report_path**: `reports/<api_env>/<timestamp>/report.html`
- **summary_path**: `reports/<api_env>/<timestamp>/summary.json`

**Validations checked** (against plan.md's `validations`)
- step <n>: `<helper>` — matched: yes|no <br>&nbsp;&nbsp;<note if no>

**Schema checked** (against plan.md's `schema_expectations`)
- step <n>: `<schema_key>|none` — matched: yes|no

**Intent alignment** (against testcase.md's Setup/Act/Assert)
- <one line: does the outcome match what the scenario was meant to prove>

**Findings**
- <one bullet per issue, or `none` — each tagged `routes to: test-creator|test-plan|none`>

---

### Filled example

# Users -- Execution Report

## test_delete_user

- **run_at**: `2026-08-29T10:14:02Z`
- **target**: `tests/users/test_users.py :: TestUsers :: test_delete_user`
- **command**: `pytest tests/users/test_users.py::TestUsers::test_delete_user`
- **outcome**: pass
- **marker_match**: yes
- **report_path**: `reports/dev/20260829-101402/report.html`
- **summary_path**: `reports/dev/20260829-101402/summary.json`

**Validations checked** (against plan.md's `validations`)
- step 1: `assert_status(200)` — matched: yes
- step 2: `assert_status(404)` — matched: yes

**Schema checked** (against plan.md's `schema_expectations`)
- step 1: `none` — matched: yes (no body to validate, as planned)
- step 2: `none` — matched: yes

**Intent alignment** (against testcase.md's Setup/Act/Assert)
- Confirms delete removes the user: the subsequent get_user 404s, matching the scenario's intent.

**Findings**
- none
