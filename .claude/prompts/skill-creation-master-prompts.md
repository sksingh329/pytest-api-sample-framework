# Master Prompts — QA Agent Skills

Reusable prompts for (re)generating each `.claude/skills/<name>/SKILL.md` file
consistently. Use these when a skill needs to be regenerated from scratch, or
as the base when adding a brand-new skill to the QA Agent pipeline. Each
prompt assumes the shared context below is already loaded.

## Shared context (prepend to every prompt)

```
You are generating a SKILL.md for the QA Agent pipeline in this repo.

Ground rules that apply to every skill:
- Config (base_dir, test_design_dir, testcase_dir) is supplied per session,
  not hardcoded — resolve/ask for it before any file-path-dependent
  action. postman_collection_path and manual_execution_path are also
  session metadata but OPTIONAL — may be entirely absent, never gate
  anything, never override an explicit answer or a codebase pattern. A
  fillable shape for all five lives at
  .claude/templates/session-metadata.template.json. E2E conventions are
  fixed at .claude/instructions/e2e-agent-instructions.md.
- A planner never writes code. Every repo file has exactly ONE owning skill;
  no file is writable by two skills:

    test-design       design doc under test_design_dir
    testcase-writer   testcase.md
    test-plan         plan.md
    test-setup        api/constants.py, api/<x>_service.py,
                      api/payloads/<x>_payloads.py, api/schemas/<x>.py,
                      tests/conftest.py
    test-creator      tests/<feature>/test_*.py  (only)
    test-review       nothing
    execution-review  nothing
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

## test-design

```
Generate SKILL.md for "test-design".

Role: identifies test cases in plain language from a user request, asking
about every concrete ambiguity before presenting scenarios — does NOT
produce testcase.md and does NOT write code.

Must include:
- Resolve test_design_dir for the session before writing anything.
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
  ONE round of questions — never trickle one at a time, never present a
  "best guess" set of scenarios alongside unresolved questions.
- GATE: do not draft or present a single scenario while any open_questions
  entry is unresolved.
- Browse the existing codebase first so identified test cases fit
  established patterns (naming, structure) rather than being invented in
  isolation.
- If manual_execution_path was provided this session (optional session
  metadata), its notes/screenshots may be consulted as OPTIONAL REFERENCE
  for existing/expected behavior — never overrides an explicit user
  answer or codebase pattern, never closes an open_questions entry by
  itself, may be entirely absent.
- For E2E scenarios, read .claude/instructions/e2e-agent-instructions.md and follow its
  conventions; if it's missing, tell the user and ask whether to proceed
  without it or create it first.
- Present test cases as a readable list/table (scenario name + short
  description) for user review and approval before saving.
- Save the approved design under test_design_dir.
- Boundaries: never writes testcase.md; never touches repo code; never
  presents scenarios with an open question unresolved; re-runs
  append/update only new or changed entries.
```

## testcase-writer

```
Generate SKILL.md for "testcase-writer".

Role: converts an approved test-design output into structured testcase.md.
test_name is the test's identity — there is no separate test_id — and is
frozen once approved here. Does NOT identify new test cases and does NOT
write code.

Must include:
- Resolve testcase_dir for the session.
- Read the existing test_name inventory across every testcase.md under
  testcase_dir first — a new test_name must not collide with one already
  assigned.
- For each test case, derive and present these fields for explicit user
  approval before writing anything: test_name (the identity — get it right
  here, see the rule below), file_name (full path), class_name (REQUIRED,
  never n/a — see "Class grouping" below), test steps (incl. setup),
  assertion, and marker (one of the markers declared in pytest.ini).
- Never assume a fixture/setup/assertion not explicitly given or clearly
  established — ask.
- Derive file_name/class_name/test_name consistently from feature/module +
  scenario, matching existing codebase casing.
- Incorporate corrections and reconfirm before finalizing — this
  confirmation is the last chance to change test_name; only write
  testcase.md after confirmation.
- For E2E scenarios, follow .claude/instructions/e2e-agent-instructions.md.
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
  whether the target file_name already has entries under testcase_dir —
  reuse their class_name rather than deriving a new one.
- Idempotency: re-invoking on an existing testcase.md appends/updates only
  new or changed entries.
- Boundaries: never writes code; never invents test cases beyond what was
  approved in test-design; never assigns a test_name that collides with an
  existing one.
```

## test-plan

```
Generate SKILL.md for "test-plan".

Role: builds/updates plan.md for every test case across every testcase.md
under testcase_dir, resolving every building block to an exact existing
identifier. Does NOT write code and does NOT invoke any other skill.

Must include:
- Resolve testcase_dir and postman_collection_path for the session.
- MANDATORY Step 0 inventory, read once per invocation, from: tests/
  conftest.py + tests/**/conftest.py (fixtures + scope); api/schemas/**/*.py
  (literal SCHEMAS keys); api/*_service.py (BaseService subclass methods);
  api/constants.py (*Endpoints); api/payloads/*.py (build_* functions);
  core/assertions.py (assert_* + soft_assertions); pytest.ini (markers).
  A row is EXISTS only on a literal string match — never fuzzy.
- Enumerate every testcase.md under testcase_dir and every test case
  within each — never assume a single file or single test case.
- plan.md fixed structure per test_name: status, marker, file_name,
  class_name, target (file_name :: class_name :: test_name), fixtures,
  services, payloads, schema_expectations, validations, data, cleanup,
  soft_grouping, blocked_on, open_questions. Each fixture/service/payload/
  schema row carries a resolved identifier + source + EXISTS|MISSING.
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
- Idempotency: update only new/changed test_name entries on re-run.
- Boundaries: never writes repo code of any kind; never invokes test-setup
  or any other skill; never marks EXISTS without a literal inventory match.
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
- Resolve testcase_dir / plan.md location for the session.
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
- Resolve testcase_dir for the session.
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

Role: reviews a test execution/run report against plan.md and testcase.md
across ALL testcase.md files under testcase_dir, matching by test_name,
checking intended coverage/validations were actually exercised and
passed. Does NOT write code.

Must include:
- Resolve testcase_dir for the session.
- Operates over the full testcase_dir — enumerate every testcase.md file
  and every test_name within each, plus their plan.md counterparts, not
  just one file/test case.
- Take the execution/run report supplied by the user.
- For each test_name, check: was it exercised, did pass/fail align with
  plan.md's intended validations/schema_expectations, is any in-scope
  test_name missing from the run report entirely.
- Report findings per test_name.
- Boundaries: never creates/edits any repo file.
```

## test-pipeline

```
Generate SKILL.md for "test-pipeline".

Role: orchestrates test-plan → (test-setup, if BLOCKED) → test-creator →
test-review in sequence over the test cases in scope under testcase_dir,
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

When a new stage is needed that isn't one of the eight above, use this
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
