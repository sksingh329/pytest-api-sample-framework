---
name: test-setup
description: Builds the support layer a test needs before it can be written — endpoints, service, payload builder, schema, and fixture — after mandatory user approval. Invoked either by hand or by test-pipeline when a plan is BLOCKED; the approval gate applies either way.
---

# test-setup

Fills the gaps `test-plan` reported as `blocked_on`. Owns exactly the "Adding a new resource"
steps 1–5 from `docs/FRAMEWORK_NOTES.md` — endpoints, service, payload builder, schema, fixture.
`test-creator` owns step 6, the test itself; this skill never writes a test.

Invoked two ways, both equally valid: by hand when `test-plan` halts, or automatically by
`test-pipeline`'s gate when an entry is `BLOCKED`. Neither path is a shortcut — the mandatory
Approve phase below applies exactly the same regardless of who invoked this skill. `test-pipeline`
never bypasses it; being invoked from an orchestrator does not make a write silent.

## Write scope

Writes only these files, and nothing else:

- `api/constants.py` — endpoints
- `api/<x>_service.py` — service class
- `api/payloads/<x>_payloads.py` — payload builder
- `api/schemas/<x>.py` — schema
- `tests/conftest.py` (or `tests/<feature>/conftest.py`) — fixtures

Never writes `core/**`, `pytest.ini`, `environments.py`, the root `conftest.py`, or any
`test_*.py`. A gap that needs a new marker, a new assertion helper, or any `core/` change is not
this skill's to fill — report it and route to the user.

## Phases

All three are mandatory and run in order.

### 1. Plan

1. Read the current inventory before proposing anything — reuse always beats create:
   - fixtures: `tests/conftest.py`, `tests/**/conftest.py`
   - schema keys: every `SCHEMAS` dict under `api/schemas/`
   - services + methods: `api/*_service.py`
   - endpoints: `api/constants.py`
   - payload builders: `api/payloads/*.py`
2. Take the gap list from `plan.md`'s `blocked_on` entries (or from the user directly).
3. If an existing artifact already covers the need, say so and propose reusing it instead of
   creating a near-duplicate.
4. Derive each genuinely-missing artifact following the repo idioms below.

### 2. Approve — mandatory

Present, before writing anything:

- every file that will be created or modified, by path
- the exact proposed code for each
- which `blocked_on` entry each piece resolves

Wait for explicit user confirmation. Incorporate corrections and re-present. **Implementation
cannot begin without approval** — never write on assumed consent.

### 3. Implement

Write only within the write scope above, in FRAMEWORK_NOTES order (endpoints → service →
payload builder → schema → fixture). Append-only: add new definitions to an existing file, never
regenerate or reorder what's already there.

## Repo idioms to mirror

- **Endpoints** — a `<X>Endpoints` class in `api/constants.py` shaped like `UsersEndpoints`:
  `VERSION`, `BASE = f"/{VERSION}/<x>"`, `DETAIL = BASE + "/{id}"` (used via `.format(id=...)`).
- **Service** — `api/<x>_service.py`, a `BaseService` subclass setting `service_name`, one method
  per business action, always returning `ApiResponse` and never a parsed dict. Follow
  `api/users_service.py`.
- **Payload builder** — `api/payloads/<x>_payloads.py` with `build_<x>(_seed=None, **overrides)`
  and the `OMIT` sentinel for dropping keys in negative tests. Deterministic under a seed, per
  `api/payloads/users_payloads.py`.
- **Schema** — `api/schemas/<x>.py` with pydantic models (not JSON Schema files) and a
  module-level `SCHEMAS = {name: Model}` dict. Every model sets
  `model_config = ConfigDict(extra="forbid")`; use `Literal[...]` for enum-ish fields; register
  list responses directly as `list[Model]`, not a wrapper model. Follow `api/schemas/users.py`.
- **Fixture** — `tests/conftest.py`, following the existing shapes: a `<x>_service` fixture
  taking `api_client`; a `cleanup_<x>` fixture yielding a mutable id list and deleting each id
  after the test; a `created_<x>` fixture yielding the raw create `ApiResponse` and deleting it
  after. Teardown must run on pass *and* fail.

## Schema keys — check before writing

`core/schemas.py` indexes every `SCHEMAS` dict under `api_schema_dir` into one namespace, and a
duplicate key raises `ConfigError` that breaks the **entire session**, not one test. Read every
existing key first and confirm the new ones don't collide. Follow the naming convention already
set by `api/schemas/users.py`: `"<resource>"` for the single object, `"<resource>s_list"` for the
list form.

Existing keys at time of writing: `user`, `users_list`, `validation_error`.

## After this skill runs

If invoked by hand, tell the user to re-run `test-plan` — statuses in `plan.md` must be
recomputed against the new inventory before `test-creator` can proceed. If invoked by
`test-pipeline`, it re-runs `test-plan` itself as part of its own sequence. Either way, this skill
never updates `plan.md` itself.

## Boundaries

- Never writes a test file — that's `test-creator`.
- Never writes `core/**`, `pytest.ini`, `environments.py`, or the root `conftest.py`.
- Never writes without explicit approval, whether invoked by hand or by `test-pipeline`.
- Never modifies `testcase.md` or `plan.md`.
- Never resolves an `open_questions` entry — that needs a human answer, not a scaffolded
  building block; `test-pipeline` will not invoke this skill for those.
