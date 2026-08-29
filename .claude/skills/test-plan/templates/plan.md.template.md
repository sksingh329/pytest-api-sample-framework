<!--
Write template — test-plan

This is the ONLY format plan.md is written in. One file per test case, at
testCaseBaseDir/<feature>/<test_name>/plan.md — its own subfolder under the feature
folder that holds testcase.md — holding that one test_name's "### <test_name>"
section. Never grouped into one file per feature, never a different section shape.

<feature> matches the feature its testcase.md is filed under; <test_name> matches
this plan's own test_name.

To re-plan a test_name that already has a plan.md: overwrite that file in place —
it only ever holds this one test_name, so nothing else to touch or reorder. To plan
a test_name for the first time: create testCaseBaseDir/<feature>/<test_name>/plan.md
with the H1 title below, then the one section.

Field notes:
- schema_expectations rows carry `reason` whenever schema_key is `none` — say
  why there's nothing to validate (no body, an unmodeled error shape, etc.).
  source is the schema file, or `n/a` when schema_key is `none`.
- validations rows may carry a trailing `# <note>` comment to say which call in
  a multi-step scenario that check belongs to — optional, but use it whenever
  more than one call happens in the test.
-->

# <Feature> -- Plan

### <test_name>
status: READY | BLOCKED
marker: smoke | regression | contract
file_name: tests/<feature>/test_<x>.py
class_name: Test<Feature>[<Suffix>]
target: <file_name> :: <class_name> :: <test_name>
fixtures:
  - name: <fixture>   source: tests/conftest.py   status: EXISTS|MISSING
services:
  - ref: api.<x>_service.<X>Service.<method>       status: EXISTS|MISSING
payloads:
  - ref: api.payloads.<x>_payloads.build_<x>   args: <literal>   status: EXISTS|MISSING
schema_expectations:
  - step: <n>   schema_key: "<key>"|none   source: api/schemas/<x>.py|n/a   status: EXISTS|MISSING   reason: <required when schema_key is none>
validations:
  - step: <n>   helper: <core.assertions fn>   args: <literal expected value>   # <optional note>
data: <explicit _seed per build_* call, or fixed literals>
cleanup: <fixture name> | none
soft_grouping: <steps wrapped in soft_assertions(), or none>
blocked_on: []
open_questions: []

---

### Filled example

# Users -- Plan

### test_delete_user
status: READY
marker: regression
file_name: tests/users/test_users.py
class_name: TestUsers
target: tests/users/test_users.py :: TestUsers :: test_delete_user
fixtures:
  - name: users_service   source: tests/conftest.py   status: EXISTS
services:
  - ref: api.users_service.UsersService.create_user   status: EXISTS
  - ref: api.users_service.UsersService.delete_user   status: EXISTS
  - ref: api.users_service.UsersService.get_user      status: EXISTS
payloads:
  - ref: api.payloads.users_payloads.build_user   args: _seed=501   status: EXISTS
schema_expectations:
  - step: 1   schema_key: none   source: n/a   status: EXISTS   reason: delete response has no body to validate
  - step: 2   schema_key: none   source: n/a   status: EXISTS   reason: 404 error response is not a modeled schema; testcase.md only asserts status
validations:
  - step: 1   helper: assert_status   args: 200   # on delete_user response
  - step: 2   helper: assert_status   args: 404   # on get_user(user_id) response
data: build_user(_seed=501) for the setup create call
cleanup: none
soft_grouping: none
blocked_on: []
open_questions: []
