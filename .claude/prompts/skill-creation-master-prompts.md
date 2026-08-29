# Master Prompts — QA Agent Skills

Reusable prompts for (re)generating each `.claude/skills/<name>/SKILL.md` file
consistently. Use these when a skill needs to be regenerated from scratch, or
as the base when adding a brand-new skill to the QA Agent pipeline. Each
prompt assumes the shared context below is already loaded.

## Shared context (prepend to every prompt)

```
You are generating a SKILL.md for the QA Agent pipeline in this repo.

Ground rules that apply to every skill:
- Config (testCaseBaseDir) is supplied per session, not hardcoded —
  resolve/ask for it before any file-path-dependent action.
  postmanCollectionPath and manualExecutionPath are also session
  metadata but OPTIONAL — may be entirely absent, never gate anything,
  never override an explicit answer or a codebase pattern. A fillable
  shape for all three lives at
  .claude/templates/session-metadata.template.json. E2E conventions are
  fixed at .claude/instructions/e2e-agent-instructions.md.
- A planner never writes code. Every repo file has exactly ONE owning skill;
  no file is writable by two skills:

    testcase-writer   testcase.md (identifies scenarios AND writes them —
                      there is no separate design-doc step or artifact)
    test-plan         plan.md
    test-setup        api/constants.py, api/<x>_service.py,
                      api/payloads/<x>_payloads.py, api/schemas/<x>.py,
                      tests/conftest.py
    test-creator      tests/<feature>/test_*.py  (only)
    test-review       nothing
    execution-review  execution-report.md (one per test_name, alongside
                      that test_name's testcase.md/plan.md)
    test-pipeline     nothing (orchestrates; writes only via the above)
    nobody (human)    core/**, pytest.ini, environments.py, root conftest.py

- plan.md NAMES what exists rather than describing what is needed. Every
  fixture/service/payload/schema row carries a resolved identifier plus a
  status of EXISTS or MISSING, decided by literal string match against a
  repo inventory — never fuzzy "close enough" matching.
- The gate is mechanical and fail-closed: a test_name's entry is READY only when
  blocked_on is empty AND open_questions is empty AND every row is EXISTS.
  Any inconsistency is treated as BLOCKED.
- open_questions ("I need an answer from you") and blocked_on ("a building
  block must be built first") are separate fields and must never be
  conflated.
- Never invent a fixture, schema, service, payload builder, or endpoint —
  mark it MISSING and halt to test-setup. There is no "user-confirmed"
  escape hatch: a yes in chat is exactly the non-deterministic path this
  design removes.
- test-setup is invoked either by hand or by test-pipeline's gate when an
  entry is BLOCKED — either way its mandatory Approve phase applies in
  full; being invoked from an orchestrator never bypasses it. After it
  runs, test-plan must re-run so statuses are recomputed. test-setup is
  never invoked for an open_questions ambiguity — only for a MISSING
  building block; that distinction stays a human-only halt.
- test_name is assigned once (by testcase-writer), never changes, and is
  carried unchanged through plan.md, the generated test method's name,
  that method's docstring (never a comment above it), test-review output,
  and execution-review output.
- Every test is a method inside a class — pipeline-generated code has no
  standalone test_* functions. All test_names sharing a file_name share
  one class_name (one class per file, not one per test). plan.md must
  carry test_name, class_name, and file_name before a test_name's entry
  can be READY.
- testcase.md and plan.md follow fixed schemas — never reorder, rename, or
  drop sections when regenerating.
- Re-invoking a skill on an existing artifact appends/updates only new or
  changed entries — never regenerates the whole artifact from scratch.
- Deterministic test data by default: an explicit _seed per build_* call,
  never randomization, unless the user explicitly asks otherwise.
- file_name / class_name / test_name are derived consistently from the
  feature/module name and scenario, matching existing codebase casing.
  class_name: Test<Feature>[<Suffix>] (e.g. TestUsers, TestUsersE2E).

Output format: a single SKILL.md with YAML frontmatter (name, description)
followed by markdown sections: a one-line role statement, then Steps,
then Boundaries (and any skill-specific sections in between).
```

---

## testcase-writer

```
Generate SKILL.md for "testcase-writer".

Role: identifies test cases from a request, asking about every concrete
ambiguity, and writes them DIRECTLY to structured testcase.md — no
intermediate design doc, no separate design step. test_name is the
test's identity — there is no separate test_id — and is frozen once
approved. Does NOT write code. One file per test case:
testCaseBaseDir/<feature>/<test_name>/testcase.md — its own subfolder,
named for the test_name, alongside where that test_name's plan.md will
live. Never grouped into one file per feature (testcase.md and plan.md
must use the same one-per-test_name shape — that's the point). <feature>
is the directory segment right after tests/ in file_name.

Must include:
- Resolve testCaseBaseDir for the session before writing anything.
- NEVER ASSUME — concrete triggers to ask about, not judgement calls to
  make silently: scope boundary (which resource/endpoint is in scope),
  coverage depth (happy path only vs negative/boundary/permission too),
  role/auth (default/read/write/unauthenticated), E2E vs single-call,
  specific data/edge values (e.g. which flavor of "invalid email"),
  priority/marker (smoke/regression/contract), environment dependence.
  Don't ask about something the request or the codebase already answers
  unambiguously — asking about a settled point is its own failure mode.
- Collect open items as explicit open_questions; resolve what the
  codebase's established patterns genuinely settle, batch the rest into
  ONE round of questions — never trickle one at a time, never present or
  derive testcase fields alongside unresolved questions.
- GATE: do not derive or present a single test case's fields while any
  open_questions entry is unresolved.
- Browse the existing codebase first so identified test cases fit
  established patterns (naming, structure) rather than being invented in
  isolation.
- If manualExecutionPath was provided this session (optional session
  metadata), its notes/screenshots may be consulted as OPTIONAL REFERENCE
  for existing/expected behavior — never overrides an explicit user
  answer or codebase pattern, never closes an open_questions entry by
  itself, may be entirely absent.
- For E2E scenarios, read .claude/instructions/e2e-agent-instructions.md and follow its
  conventions; if it's missing, tell the user and ask whether to proceed
  without it or create it first.
- Read the existing test_name inventory by listing every
  testCaseBaseDir/<feature>/<test_name>/ subfolder first — a new
  test_name must not collide with one already assigned anywhere.
- For each identified test case, derive these fields, then present them
  for explicit user approval USING THE TABLE in
  templates/testcase-presentation.md — never prose, never a bulleted list.
  Fixed row order: test_name (the identity — get it right here, see the
  rule below), file_name (full path), class_name (REQUIRED, never n/a —
  see "Class grouping" below), marker (one of the markers declared in
  pytest.ini), Setup (arrange step(s) — fixtures/service calls, any
  captured value), Act (the single action under test), Assert (every
  check, numbered, in run order). Never write before that approval.
- PRESENTATION FORMAT is mandatory — one table per test case, that exact
  row set, never reordered/renamed/merged/dropped. See
  templates/testcase-presentation.md for row-by-row guidance and a
  filled example.
- WRITE FORMAT is mandatory and DIFFERENT from the presentation table —
  testcase.md itself follows templates/testcase.md.template.md exactly:
  one "# <Feature> -- Test Case" H1, then the one "## <test_name>"
  section with file_name/class_name/marker as a bullet list, then bold
  "Setup" / "Steps (Act)" / "Assertions" subheadings each with their own
  bullet list. Never any other shape.
- Never assume a fixture/setup/assertion not explicitly given or clearly
  established — ask.
- Derive file_name/class_name/test_name consistently from feature/module +
  scenario, matching existing codebase casing.
- Incorporate corrections and reconfirm before finalizing — this
  confirmation is the last chance to change test_name; only write
  testCaseBaseDir/<feature>/<test_name>/testcase.md after confirmation.
- test_name rule (identity, frozen after approval): no separate test_id —
  test_name IS the identity. Once approved, frozen — never changes
  afterward, even for a typo/clarity fix; carried unchanged into plan.md,
  the generated test method's name, that method's docstring, test-review
  output, execution-review output. A genuine rename is a delete-and-recreate
  (retire the old entry, create a new test_name), not an edit.
- CLASS GROUPING: every test belongs to a class — no standalone test
  functions in pipeline-generated code. All test_names sharing a file_name
  must share the same class_name (one class per file). Derive class_name
  as Test<PascalCase(feature)>[<PascalCase(suffix)>] (e.g. TestUsers,
  TestUsersE2E, TestUsersAuth). Before assigning a new class_name, check
  whether any other testcase.md under testCaseBaseDir already targets the
  same file_name — reuse its class_name rather than deriving a new one.
- Idempotency: each test_name owns exactly one file
  (testCaseBaseDir/<feature>/<test_name>/testcase.md); re-invoking on an
  existing test_name overwrites only that file, never another's. A new
  test case always means a new <test_name>/ folder.
- Boundaries: never writes code; never writes anything beyond
  testCaseBaseDir/<feature>/<test_name>/testcase.md (no intermediate
  design doc); never presents/writes fields with an open question
  unresolved; never assigns a test_name that collides with an existing
  one (or existing subfolder) anywhere; never writes testcase.md in any
  shape other than the template's; never puts more than one test case's
  fields into a single testcase.md.
```

## test-plan

```
Generate SKILL.md for "test-plan".

Role: builds/updates plan.md for every test case across every testcase.md
under testCaseBaseDir, resolving every building block to an exact existing
identifier. Does NOT write code and does NOT invoke any other skill.
plan.md is one-per-test-case, at testCaseBaseDir/<feature>/<test_name>/
plan.md — the same folder as that test_name's testcase.md. Never grouped
into one file per feature. WRITE FORMAT is mandatory, from
templates/plan.md.template.md.

Must include:
- Resolve testCaseBaseDir and postmanCollectionPath for the session.
- MANDATORY Step 0 inventory, read once per invocation, from: tests/
  conftest.py + tests/**/conftest.py (fixtures + scope); api/schemas/**/*.py
  (literal SCHEMAS keys); api/*_service.py (BaseService subclass methods);
  api/constants.py (*Endpoints); api/payloads/*.py (build_* functions);
  core/assertions.py (assert_* + soft_assertions); pytest.ini (markers).
  A row is EXISTS only on a literal string match — never fuzzy.
- Enumerate every testcase.md under testCaseBaseDir and every test case
  within each — never assume a single file or single test case.
- plan.md fixed structure per test_name (see templates/plan.md.template.md
  for the full skeleton and a filled example): status, marker, file_name,
  class_name, target (file_name :: class_name :: test_name), fixtures,
  services, payloads, schema_expectations, validations, data, cleanup,
  soft_grouping, blocked_on, open_questions. Each fixture/service/payload/
  schema row carries a resolved identifier + source + EXISTS|MISSING.
  schema_expectations rows carry a REQUIRED reason whenever schema_key is
  none (source becomes n/a too). validations rows may carry a trailing
  "# <note>" comment naming which call, in a multi-step scenario, that
  check belongs to.
- file_name/class_name/test_name are carried verbatim from testcase.md,
  never re-derived here — missing one is an open_questions entry, not a
  guess. Every test_name sharing a file_name must carry the same
  class_name; a mismatch across entries for the same file is a plan
  defect (stop and ask).
- The gate: READY only when test_name/class_name/file_name are all present
  AND blocked_on empty AND open_questions empty AND every row EXISTS; any
  inconsistency → BLOCKED (fail closed).
- validation-planner stays an INTERNAL step that writes no code —
  validations compose core/assertions.py helpers, which always exist, so
  validations never block.
- Pin the determinism fields: marker (from pytest.ini), target (full path),
  explicit _seed per build_* call, cleanup fixture, soft_grouping, and a
  step number on every validation/schema row.
- On gaps: emit ONE consolidated halt listing every gap with a
  copy-pasteable invocation. Route to test-setup for fixture/schema/service/
  payload/endpoint; route to the human for a new marker or a core/ change.
- Source precedence on conflicts: (1) testcase.md, (2) existing codebase
  patterns / the inventory, (3) Postman collection JSON. Unresolvable
  conflict → stop and ask the user.
- For E2E plans, also consult .claude/instructions/e2e-agent-instructions.md.
- Write/update testCaseBaseDir/<feature>/<test_name>/plan.md for each
  in-scope test_name, preserving the fixed structure.
- OUTCOME PRESENTATION is mandatory — after resolving each test_name,
  present it in the table from templates/plan-outcome-presentation.md:
  title "<test_name> -> status: READY|BLOCKED", fixed row order fixtures,
  services, payloads, schema_expectations, validations, cleanup (plus
  soft_grouping if not none, blocked_on if BLOCKED, open_questions if
  non-empty). This is a REPORT, not an approval gate — test-plan still
  writes plan.md itself without waiting on the user.
- Idempotency: re-invoking on a test_name with an existing plan.md
  overwrites only that test_name's file, never another's.
- Boundaries: never writes repo code of any kind; never invokes test-setup
  or any other skill; never marks EXISTS without a literal inventory match;
  never writes plan.md anywhere but
  testCaseBaseDir/<feature>/<test_name>/plan.md; never writes plan.md in
  any shape other than the template's.
```

## test-setup

```
Generate SKILL.md for "test-setup".

Role: builds the support layer a test needs before it can be written —
endpoints, service, payload builder, schema, and fixture — after mandatory
user approval. Invoked either by hand or by test-pipeline's gate when a
plan is BLOCKED; the approval gate applies identically either way — being
invoked from an orchestrator never makes the write silent. Owns
FRAMEWORK_NOTES "Adding a new resource" steps 1-5; test-creator owns
step 6 (the test).

Must include:
- Write scope, exclusively: api/constants.py, api/<x>_service.py,
  api/payloads/<x>_payloads.py, api/schemas/<x>.py, tests/conftest.py.
  Never core/**, pytest.ini, environments.py, root conftest.py, or any
  test_*.py.
- THREE MANDATORY PHASES in order:
  1. Plan — read the current inventory first (reuse beats create); take the
     gap list from plan.md's blocked_on; propose reusing an existing
     artifact rather than creating a near-duplicate.
  2. Approve — present every file to be touched, the exact proposed code,
     and which blocked_on entry each piece resolves; wait for explicit user
     confirmation. Implementation CANNOT begin without it.
  3. Implement — write only within scope, in FRAMEWORK_NOTES order
     (endpoints → service → payload → schema → fixture), append-only.
- Repo idioms to mirror: <X>Endpoints shaped like UsersEndpoints; a
  BaseService subclass with service_name and one method per business action
  always returning ApiResponse; build_<x>(_seed=None, **overrides) with the
  OMIT sentinel; pydantic schemas with ConfigDict(extra="forbid"), Literal
  for enum-ish fields, list responses as list[Model]; <x>_service /
  cleanup_<x> yield-list / created_<x> yield-response fixture shapes.
- Schema key collision check: core/schemas.py indexes all SCHEMAS dicts
  into ONE namespace and a duplicate key raises ConfigError that breaks the
  entire session, not one test. Read every existing key first; follow the
  "<resource>" / "<resource>s_list" convention.
- After running: if invoked by hand, tell the user to re-run test-plan so
  statuses are recomputed; if invoked by test-pipeline, it re-runs
  test-plan itself. This skill never updates plan.md itself.
- Boundaries: never writes a test file; never writes without explicit
  approval, whether invoked by hand or by test-pipeline; never resolves an
  open_questions entry (a human-only halt, not something test-pipeline
  routes here); never modifies testcase.md or plan.md.
```

## test-creator

```
Generate SKILL.md for "test-creator".

Role: writes test files from a READY plan.md, composing ONLY building
blocks the plan already resolved to existing identifiers. Wiring, not
invention.

Must include:
- Resolve testCaseBaseDir / plan.md location for the session.
- Write scope: tests/<feature>/test_*.py ONLY. Never tests/conftest.py,
  never api/**, never core/**, never pytest.ini.
- Precondition: every in-scope test_name has status READY — meaning
  test_name/class_name/file_name are all present, blocked_on empty,
  open_questions empty, every row EXISTS. Any BLOCKED → write NOTHING (no
  partial generation), print that entry's blocked_on, and tell the user to
  invoke test-setup or make the human-only change.
- Re-verify each EXISTS row against the live repo (quick grep) before
  writing — plan.md may be stale; trust the repo, not the plan.
- CLOSED-WORLD RULE: the test may reference only identifiers listed in
  that test_name's fixtures/services/payloads/schema_expectations/
  validations rows. Scope this to EXTERNAL references only — ordinary
  Python in the body (locals, loops, chained ids like
  created_id = response.json()["id"]) stays free. Needing anything
  unlisted is a PLAN DEFECT: stop and route back to test-plan. Do NOT
  include escape hatches like "or clearly established codebase pattern"
  or "or user-confirmed".
- CLASS GROUPING: every test is a method inside a class — no standalone
  test_* functions. All test_names sharing a file_name go into the SAME
  class in that file, never split across multiple classes and never one
  class per method. Method signature: def <test_name>(self, <fixtures in
  plan order>). If the target file already has the class from an earlier
  run, ADD the method to it — never create a second class with the same
  name. A class_name mismatch against an existing class in that file is a
  plan defect: stop, don't write, route back to test-plan.
- Apply the plan verbatim: marker, data seeds, soft_grouping wrapping,
  cleanup fixture (never an inline try/finally teardown).
- Assert only through core/assertions.py — a bare assert produces no
  report record and is invisible to execution-review.
- Each generated test method gets a DOCSTRING (never a comment above the
  method) restating its test_name plus a one-line description — the only
  place traceability is recorded.
- Use file_name/class_name/test_name exactly as given in plan.md — don't
  reinvent.
- For E2E tests, follow .claude/instructions/e2e-agent-instructions.md.
- Boundaries: writes only test files; never creates a fixture, schema,
  service, payload builder, or endpoint (that's test-setup); never
  modifies testcase.md or plan.md.
```

## test-review

```
Generate SKILL.md for "test-review".

Role: reviews test code created by test-creator against plan.md (and
testcase.md for original intent), matching by test_name. Does NOT write
code — read-only review.

Must include:
- Resolve testCaseBaseDir for the session.
- For each test_name in scope, locate the testcase.md entry, the plan.md
  entry, and the generated test code (matched via the test_name docstring
  left by test-creator).
- TWO PASSES, in order.
- Pass 1, MECHANICAL conformance (yes/no checks, not judgement): the
  method's class_name matches plan.md and it IS a method (self as first
  param) inside that class, never a standalone function — every test_name
  sharing a file_name lives in the SAME class, a second class for the same
  file is a violation; fixtures used ⊆ plan fixtures AND plan fixtures ⊆
  used (both directions — an extra is a deviation, an unused one is plan
  drift); every assert_schema key literal appears in schema_expectations;
  every assert_* exists in core/assertions.py AND in validations; marker
  matches the plan; ZERO bare assert statements; no core.http_client /
  core.auth / core.config / requests import in a test file; every file
  touched is under tests/<feature>/test_*.py (a write to conftest.py or
  api/** is a scope violation); the plan's cleanup fixture is wired with
  no inline try/finally; every test carries a docstring restating its
  test_name — a comment above the method instead is a conformance
  failure, not a stylistic variant.
- Pass 2, JUDGEMENT: deviations (code does something not called for), gaps
  (requirements not exercised), missing coverage (test_names with no
  corresponding code), and for E2E that steps run in the plan's step order
  with the producer the plan names for each chained value.
- Report findings per test_name, referencing file/line where possible.
- Boundaries: never creates/edits any repo file; never fixes what it
  finds — route the fix to the owning skill (test-creator for test code,
  test-setup for a missing building block, test-plan for a plan defect).
```

## execution-review

```
Generate SKILL.md for "execution-review".

Role: RUNS the newly created test(s) via pytest, then reviews the
resulting report against plan.md and testcase.md across ALL testcase.md
files under testCaseBaseDir, matching by test_name, and WRITES one
execution-report.md per test_name capturing that outcome. The only skill
that executes pytest. Never writes test code, plan.md, or testcase.md —
running a test is not editing one, and execution-report.md is a new file,
not an edit to either.

Must include:
- Resolve testCaseBaseDir for the session.
- Operates over the full testCaseBaseDir — enumerate every testcase.md file
  and every test_name within each, plus each one's own plan.md
  (testCaseBaseDir/<feature>/<test_name>/plan.md), not just one file/case.
- SCOPE: named test case(s)/feature run only those; if nothing named, run
  every in-scope test_name with plan.md status READY (never BLOCKED — no
  code exists for it). A named BLOCKED test_name: stop for that one, don't
  silently skip and run nothing.
- RUN: for each in-scope test_name, read plan.md's target (file_name ::
  class_name :: test_name) and run pytest <file_name>::<class_name>::
  <test_name> precisely (e.g. pytest tests/users/test_users.py::TestUsers
  ::test_delete_user); group multiple targets into one invocation.
  Default api_env=dev unless the user names another (API_ENV=<env>
  pytest ...); never edit pytest.ini/.env/environments.py/core/** to make
  a run pass — report the failure instead.
- Locate evidence: reports/<api_env>/<timestamp>/report.html,
  summary.json, and the per-worker ledger under reports/<api_env>/ledger/
  for assertion-level detail.
- For each test_name, check: did it collect and run, did pass/fail align
  with plan.md's validations/schema_expectations, does the marker match,
  does the outcome match testcase.md's Setup/Act/Assert intent, is any
  in-scope test_name missing from the run entirely.
- A run that reveals plan.md itself is wrong (e.g. an EXISTS fixture that
  errors, a file_name/class_name mismatch) is a PLAN DEFECT — report it
  and route back to test-plan, not just a test failure.
- Report findings per test_name, referencing the report path and
  file/line where possible.
- WRITE FORMAT is mandatory, from
  templates/execution-report.md.template.md — one file per test_name at
  testCaseBaseDir/<feature>/<test_name>/execution-report.md, the same
  subfolder as that test_name's testcase.md/plan.md. Fixed shape: run_at,
  target, command, outcome, marker_match, report_path, summary_path, then
  Validations checked / Schema checked (each row copied from plan.md's own
  step numbers, marked matched: yes|no against the evidence), an Intent
  alignment line against testcase.md's Setup/Act/Assert, and a Findings
  list (none only when the run is clean end-to-end), each finding tagged
  routes to: test-creator|test-plan|none.
- Idempotency: re-running on a test_name that already has a report
  overwrites only that file with the latest run — it holds the most recent
  execution, not a history; never touches another test_name's report.
- Boundaries: runs pytest (the only skill that does); never creates/edits
  test code, plan.md, or testcase.md; writes only that test_name's
  execution-report.md, in the template's exact shape, and no other repo
  file; never edits pytest.ini/.env/environments.py/core/** to make a run
  pass; never runs a BLOCKED test_name.
```

## test-pipeline

```
Generate SKILL.md for "test-pipeline".

Role: orchestrates test-plan → (test-setup, if BLOCKED) → test-creator →
test-review in sequence over the test cases in scope under testCaseBaseDir,
passing output forward at each stage.

Must include:
- Confirm scope with the user (which testcase.md file(s)/test_name(s)) before
  starting.
- Invoke test-plan for that scope.
- GATE: check every in-scope test_name. Treat any inconsistency between
  status, blocked_on, and per-row statuses as BLOCKED — fail closed.
    - all READY → continue to test-creator.
    - any BLOCKED → invoke test-setup (see below).
    - any open_questions non-empty → halt entirely, hand control back to
      the user; do NOT invoke test-setup for this — it only fills MISSING
      building blocks, not ambiguity.
- test-setup IS invoked automatically by this pipeline's gate on BLOCKED.
  Its own mandatory Approve phase still applies in full — the pipeline
  never bypasses it; chaining into test-setup does not make the write
  silent. test-setup remains separately invocable by hand too.
- RE-ENTRY: after test-setup finishes, return to test-plan (not
  test-creator) so every status is recomputed against the new inventory.
  Never carry forward statuses from before a test-setup run.
- Invoke test-creator using the READY entries, then test-review.
- Summarize the end-to-end result (plan produced, any setup performed,
  code generated, review findings) to the user.
- Boundaries: writes nothing itself; the test-setup step writes only its
  own scope and only after its own approval; the test-creator step writes
  code and only tests/<feature>/test_*.py. Halts entirely (no test-setup
  invocation) on open_questions. Does not include running the tests or
  execution-review (those are separate, user-triggered steps).
```

---

## Adding a brand-new skill

When a new stage is needed that isn't one of the seven above, use this
template, filling in the bracketed parts, and route it into the QA Agent's
"Routing logic" and "Skills" sections once approved:

```
Generate SKILL.md for "[skill-name]".

Role: [one sentence — what it does and, if applicable, what it explicitly
does NOT do].

Must include:
- [Which config keys it resolves, and when to ask the user for them.]
- [What it reads (testcase.md / plan.md / code / execution report / other).]
- [What it produces, if anything, and under which config-resolved path.]
- [Any fixed schema its output must follow, if it produces an artifact.]
- [Whether/how it touches .claude/instructions/e2e-agent-instructions.md for E2E scope.]
- [Idempotency behavior on re-invocation, if it writes an artifact.]
- Boundaries: [does it write code? If not, say so explicitly — only
  test-creator writes code by default.]
```

After generating, get the user's confirmation on the fields before writing
the file, same as any other artifact-producing step in this pipeline.
