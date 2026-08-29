---
name: test-design
description: Identifies test cases in plain language from a user request, grounded in existing codebase patterns, asking about every concrete ambiguity before presenting scenarios. Does not produce testcase.md and does not write code.
---

# test-design

Isolated skill. Focuses solely on *identifying* test cases — it does not produce `testcase.md`.

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

1. Resolve `test_design_dir` for this session (session metadata — ask the user if not yet
   provided this session).
2. Read the request against the "Never assume" list above. Collect every open item as an
   `open_questions` entry — don't resolve any of them by guessing.
3. Browse the existing codebase to understand established patterns (how similar features/
   endpoints are already tested, naming, structure) so identified test cases fit what already
   exists rather than being invented in isolation. This can *close* an open question (e.g. the
   codebase already fixes the role convention) — resolve it that way when it genuinely does,
   rather than asking about something the codebase already answers.
   - If `manual_execution_path` was provided for this session, its step-by-step notes/screenshots
     may be consulted as **optional reference** for understanding existing or expected behavior.
     It never overrides an explicit user answer or an established codebase pattern, and it never
     closes an `open_questions` entry by itself — if it only hints at an answer, still ask. It may
     be entirely absent.
4. For E2E scenarios, read the repo's E2E reference (`.claude/instructions/e2e-agent-instructions.md`) and follow
   its structure/conventions instead of inventing new ones. If it doesn't exist yet, tell the user
   and ask whether to proceed without it or create it first.
5. **Gate**: if any `open_questions` entry is still unresolved, stop here and ask the user — in
   one batched round, not one-by-one — before drafting a single scenario. Do not present a
   "best guess" set of scenarios alongside the questions; resolve first, present second.
6. Present the identified test cases back to the user in a clear, readable format (an organized
   list or table of scenario names and short descriptions) for review — this is a plain-language
   design, not yet `testcase.md`.
7. On approval, save the design under `test_design_dir`. Do not write `testcase.md` — that's
   testcase-writer's job.

## Boundaries

- Never creates or edits test code or any other repo file.
- Never produces `testcase.md`.
- Never presents scenarios while an open question from step 2 remains unresolved.
- If re-invoked on an existing design doc (e.g. adding more scenarios), append/update only the
  new or changed entries — don't regenerate the whole doc.
