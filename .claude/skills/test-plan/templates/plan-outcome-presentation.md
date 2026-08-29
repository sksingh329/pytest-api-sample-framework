<!--
Outcome presentation template — test-plan

After resolving a test_name's plan.md entry (READY or BLOCKED), present the
outcome to the user in exactly this table shape — one table per test_name.
This is how test-plan reports what it resolved; it is not an approval gate
(test-plan writes plan.md itself, it doesn't wait on the user) — the table
exists so the user can see, row by row, why each identifier came out
EXISTS/MISSING and why the whole entry landed READY or BLOCKED, without
reading the raw plan.md.

Title line: "<test_name> -> status: READY|BLOCKED"

Row order is fixed: fixtures, services, payloads, schema_expectations,
validations, cleanup. Add soft_grouping only when it isn't "none"; add
blocked_on only when the entry is BLOCKED (one line per gap, naming the
remediation); add open_questions only when non-empty. Never reorder or drop
a row that applies.

Resolution column style: name each identifier, its EXISTS/MISSING status,
and the one-line reason a reader would otherwise have to infer — a pinned
seed and why, a schema gap and why, which call a validation targets. Terse,
not a repeat of the raw plan.md fields.
-->

**`<test_name>` → status: `<READY|BLOCKED>`**

| Row | Resolution |
|---|---|
| fixtures | `<fixture>` (`<source>`) — `<EXISTS\|MISSING>` |
| services | `<method>`, `<method>`, ... on `<Service>` — `<all EXISTS \| which are MISSING>` |
| payloads | `<build_x(_seed=n)>` — `<EXISTS>` (`<why this seed>`) |
| schema_expectations | `<per-step summary — schema_key or "none" and why>` |
| validations | `step <n>: <helper>(<args>)<; step <n>: ...>` |
| cleanup | `<fixture name> \| none — <why>` |

---

### Filled example

**`test_delete_user` → status: `READY`**

| Row | Resolution |
|---|---|
| fixtures | `users_service` (`tests/conftest.py`) — EXISTS |
| services | `create_user`, `delete_user`, `get_user` on `UsersService` — all EXISTS |
| payloads | `build_user(_seed=501)` — EXISTS (pinned a distinct seed so this doesn't collide with other unseeded `build_user()` calls, which all default to seed 42) |
| schema_expectations | none for either step — the delete response has no body, and the 404 error isn't a modeled schema; `testcase.md` only calls for status checks |
| validations | step 1: `assert_status(delete_response, 200)`; step 2: `assert_status(get_response, 404)` |
| cleanup | none — deliberate, since the Act step itself deletes the user |
