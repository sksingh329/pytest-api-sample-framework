<!--
Write template — testcase-writer

This is the ONLY format testcase.md is written in. One file per test case, at
testCaseBaseDir/<feature>/<test_name>/testcase.md — its own subfolder under the
feature folder, named for the test_name it describes. plan.md for this same
test_name lives alongside it, in the same folder, once test-plan runs. Never
grouped into one file per feature, never a different section shape.

<feature> is the directory segment right after tests/ in file_name (e.g.
file_name tests/users/test_users.py -> feature "users").

To re-describe a test_name that already has a testcase.md: overwrite that file
in place — it only ever holds this one test_name, so nothing else to touch. To
describe a test_name for the first time: create
testCaseBaseDir/<feature>/<test_name>/testcase.md with the H1 title below, then
the one section.
-->

# <Feature> -- Test Case

## <test_name>

- **file_name**: `<file_name>`
- **class_name**: `<class_name>`
- **marker**: `<marker>`

**Setup**
- <arrange step(s) — fixtures/service calls, any captured value>

**Steps (Act)**
- <the single action under test>

**Assertions**
- <assertion 1>
- <assertion 2>
- <...>

---

### Filled example

# Users -- Test Case

## test_delete_user

- **file_name**: `tests/users/test_users.py`
- **class_name**: `TestUsers`
- **marker**: `regression`

**Setup**
- Create a new user (`users_service.create_user(**build_user())`), capture `user_id` from the response.

**Steps (Act)**
- Delete the user: `users_service.delete_user(user_id)`.

**Assertions**
- Delete response status == `200`.
- Follow-up `GET` on the same `user_id` (`users_service.get_user(user_id)`) returns status `404`.
