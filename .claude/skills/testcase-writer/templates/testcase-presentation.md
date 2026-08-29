<!--
Presentation template — testcase-writer

Before writing anything to testcase.md, present EVERY test case to the user in
exactly this table shape, one table per test case, and get explicit approval on
it. This is the only approval format this skill uses — never a prose summary,
never a bulleted list instead of the table.

Row order is fixed: test_name, file_name, class_name, marker, Setup, Act, Assert.
Never reorder, rename, merge, or drop a row.

- test_name / file_name / class_name / marker — the identity and location fields,
  exactly as testcase-writer derives them (see SKILL.md).
- Setup — the arrange step(s): fixtures used, service calls made to get into the
  starting state, and any value captured for later steps (e.g. an id). If there's
  no setup beyond the fixtures themselves, say so plainly rather than leaving the
  row implying more happened than did.
- Act — the single action under test — the one call whose behavior this test
  exists to verify. Keep this to the action itself; verification goes in Assert.
- Assert — every check as a numbered list within the cell (`1. ... <br>2. ...`),
  in the order they'll run. One test can and often should assert more than one
  thing — number them all, don't collapse into one paragraph.
-->

| Field | Value |
|---|---|
| test_name | `<test_name>` |
| file_name | `<file_name>` |
| class_name | `<class_name>` |
| marker | `<smoke\|regression\|contract>` |
| **Setup** | `<arrange step(s) — fixtures/service calls, any captured value>` |
| **Act** | `<the one action under test>` |
| **Assert** | 1. `<assertion 1>`<br>2. `<assertion 2>`<br>... |

---

### Filled example

| Field | Value |
|---|---|
| test_name | `test_delete_user` |
| file_name | `tests/users/test_users.py` |
| class_name | `TestUsers` |
| marker | `regression` |
| **Setup** | Create a new user (`users_service.create_user(**build_user())`), capture `user_id` |
| **Act** | Delete the user (`users_service.delete_user(user_id)`) |
| **Assert** | 1. Delete response status == 200<br>2. Follow-up GET on the same `user_id` returns status 404 |
