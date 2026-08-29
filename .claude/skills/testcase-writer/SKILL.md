---
name: testcase-writer
description: Identifies test cases from a request, asking about every concrete ambiguity, and writes them directly to structured testcase.md after explicit field-by-field approval. test_name is the test's identity — frozen once approved. Does not write code.
---

# testcase-writer

Takes a user request and produces `testcase.md` directly — there is no intermediate
plain-language design doc and no separate design step. Identifying scenarios and writing them as
structured fields are one skill now: ask what's ambiguous, derive the fields, get explicit
approval, write.

`testcase.md` is consumed by test-plan, test-creator, test-review, and execution-review. One file
per test case, at `testCaseBaseDir/<feature>/<test_name>/testcase.md` — its own subfolder under
the feature folder, named for the `test_name` it describes. `plan.md` for this same `test_name`
lives alongside it, in the same folder, once `test-plan` runs. Never grouped into one file per
feature — that model caused confusion between `testcase.md` and `plan.md` having different
groupings, so both now use exactly this same one-per-`test_name` shape. `<feature>` is the
directory segment right after `tests/` in `file_name` (e.g. `file_name` `tests/users/test_users.py`
→ feature `users`).

## Never assume — ask instead

A request for "tests for X" always underspecifies something. Filling that gap with a plausible
guess is exactly what this skill must not do — a guessed scope silently narrows or widens
coverage, and nobody notices until execution-review finds the gap much later. Treat each of these
as a concrete trigger to ask, not a judgement call to make silently:

- **Scope boundary** — which resource(s)/endpoint(s) are in scope? "Test the users API" doesn't
  say whether list/get/create/update/delete are all in scope, or just the one the user mentioned.
- **Coverage depth** — happy path only, or negative/boundary/permission cases too? Don't default
  to "happy path only" just because it wasn't said.
- **Role / auth** — which role (`default`/`read`/`write`, or unauthenticated)? A scenario that
  doesn't name one is ambiguous, not "use default."
- **E2E vs single-call** — does this need a multi-step chained scenario (see
  `.claude/instructions/e2e-agent-instructions.md`) or a set of independent single-call tests? Don't decide this
  from tone; ask if it's not explicit.
- **Specific data / edge values** — "invalid email" could mean malformed, empty, too long, or
  wrong type. Ask which, or ask if all of them are wanted as separate cases.
- **Priority / marker** — is this `smoke`, `regression`, or `contract` work? This affects how many
  scenarios are worth designing (smoke stays minimal by definition).
- **Environment** — does the scenario depend on environment-specific data (dev vs stage), or is
  it environment-agnostic?

If the request already answers one of these unambiguously, don't ask about it — asking about
something already stated is its own failure mode. Ask only what's genuinely open, batched into
one round, not trickled one question at a time.

## Steps

1. Resolve `testCaseBaseDir` for this session (ask if not yet provided).
2. Read the request against the "Never assume" list above. Collect every open item as an
   `open_questions` set — don't resolve any of them by guessing.
3. Browse the existing codebase to understand established patterns (how similar features/
   endpoints are already tested, naming, structure) so identified test cases fit what already
   exists rather than being invented in isolation. This can *close* an open question (e.g. the
   codebase already fixes the role convention) — resolve it that way when it genuinely does,
   rather than asking about something the codebase already answers.
   - If `manualExecutionPath` was provided for this session, its step-by-step notes/screenshots
     may be consulted as **optional reference** for understanding existing or expected behavior.
     It never overrides an explicit user answer or an established codebase pattern, and it never
     closes an open question by itself — if it only hints at an answer, still ask. It may be
     entirely absent.
4. For E2E scenarios, read the repo's E2E reference (`.claude/instructions/e2e-agent-instructions.md`)
   and follow its structure/conventions instead of inventing new ones. If it doesn't exist yet,
   tell the user and ask whether to proceed without it or create it first.
5. **Gate**: if any open item is still unresolved, stop here and ask the user — in one batched
   round, not one-by-one. Do not derive or present testcase fields alongside open questions;
   resolve first, derive second.
6. Read the existing inventory of `test_name`s by listing every
   `testCaseBaseDir/<feature>/<test_name>/` subfolder — a new `test_name` must not collide with
   one already assigned anywhere under `testCaseBaseDir`.
7. For each identified test case, derive these fields, then present them to the user for
   explicit approval **using the table in `templates/testcase-presentation.md`** — see
   "Presentation format" below. Never write anything before that approval.
   - `test_name` — this is the test's identity (see the rule below); get it right here
   - `file_name` (full path, e.g. `tests/users/test_users_e2e.py`)
   - `class_name` — every test belongs to a class; there are no standalone test functions in
     pipeline-generated code (see "Class grouping" below). Required, never `n/a`.
   - `marker` — one of the markers declared in `pytest.ini` (`smoke`, `regression`, `contract`)
   - `Setup` — the arrange step(s): fixtures/service calls to reach the starting state, and any
     value captured for later use (e.g. an id)
   - `Act` — the single action under test
   - `Assert` — every check, numbered, in run order — a test asserting more than one thing lists
     all of them, never collapsed into one line
8. Never assume a fixture, setup step, or assertion not explicitly given or clearly established in
   existing codebase patterns — ask the user.
9. Derive `file_name`, `class_name`, and `test_name` consistently from the feature/module name and
   scenario, matching existing codebase casing conventions.
10. Incorporate any corrections the user requests and reconfirm before finalizing — this
    confirmation is the last chance to change `test_name`; see the rule below.
11. Only after confirmation, write/update
    `testCaseBaseDir/<feature>/<test_name>/testcase.md` — see "Write format" below for its exact
    shape.

## Presentation format — mandatory

Every test case is presented for approval as the exact table in
`templates/testcase-presentation.md` — never as prose, never as a bulleted list, never any other
shape. One table per test case. Row order is fixed: `test_name`, `file_name`, `class_name`,
`marker`, `Setup`, `Act`, `Assert`; never reorder, rename, merge, or drop a row. See that file for
the row-by-row guidance and a filled example.

This is the presentation step, not the write step — `testcase.md` itself still gets written only
after the user approves what the table shows, and in a different shape (see below).

## Write format — mandatory

`testcase.md` itself is written in the exact shape of `templates/testcase.md.template.md` — never
any other structure:

```
# <Feature> -- Test Case

## <test_name>

- **file_name**: `<file_name>`
- **class_name**: `<class_name>`
- **marker**: `<marker>`

**Setup**
- <arrange step(s)>

**Steps (Act)**
- <the single action under test>

**Assertions**
- <assertion 1>
- <assertion 2>
```

One file, one `## <test_name>` section — the file only ever describes the one `test_name` it's
named for. See the template file for a filled example.

## `test_name` rule — identity, frozen after approval

There is no separate `test_id`: `test_name` **is** the identity carried through the rest of the
pipeline. Once approved in step 10, it is frozen — it must be carried unchanged into `plan.md`,
the generated test method's name, that method's docstring, `test-review` output, and
`execution-review` output.

`test_name` never changes after approval, even for a typo or clarity fix. A genuine rename is a
delete-and-recreate — retire the old entry (and its downstream `plan.md`/code/review history) and
create a new one with a new `test_name` — never an in-place edit. This is why step 6's collision
check and step 10's last-chance confirmation matter: get it right before it's frozen.

## Class grouping

Every test belongs to a class — `class_name` is required, never `n/a`, and there are no
standalone test functions in pipeline-generated code (`test-creator` never writes one outside a
class). All test cases that share a `file_name` must share the same `class_name` — one class per
file, not one class per test. Derive `class_name` as `Test<PascalCase(feature)>` for a file's
primary class (e.g. `TestUsers` for `tests/users/test_users.py`), or
`Test<PascalCase(feature)><PascalCase(suffix)>` when the file name carries a suffix (e.g.
`TestUsersE2E` for `tests/users/test_users_e2e.py`, `TestUsersAuth` for
`tests/users/test_users_auth.py`).

Before assigning a new `class_name`, check whether any other `testCaseBaseDir/<feature>/<*>/
testcase.md` already targets the same `file_name` — if one does, reuse its `class_name` rather
than deriving a new one; a mismatch would split one file's tests across two classes.

## Idempotency

Each `test_name` owns exactly one file: `testCaseBaseDir/<feature>/<test_name>/testcase.md`.
Re-invoking this skill for a `test_name` that already has one overwrites only that file — it
never touches any other `test_name`'s `testcase.md`. Adding a new test case never means editing
an existing file; it means creating a new `<test_name>/` folder with its own `testcase.md`.

## Boundaries

- Never creates or edits test code or any other repo file.
- Never writes anything beyond `testCaseBaseDir/<feature>/<test_name>/testcase.md` — no
  intermediate design doc, no `test_design_dir`.
- Never presents or writes testcase fields while an open question from step 2 remains unresolved.
- Never assigns a `test_name` that collides with an existing one (or existing subfolder) anywhere
  under `testCaseBaseDir`.
- Never writes `testcase.md` in any shape other than `templates/testcase.md.template.md`'s.
- Never puts more than one test case's fields into a single `testcase.md`.
