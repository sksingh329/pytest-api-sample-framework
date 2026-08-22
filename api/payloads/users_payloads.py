"""Builds a valid /users request body from zero arguments. Any field is
overridable (pass a new value) or removable (pass OMIT) for negative
tests -- e.g. build_user(email=OMIT) to test a missing-required-field
case. Randomised values are deterministic under a seed, so a failing test
is reproducible.
"""
from __future__ import annotations

import random

OMIT = object()  # build_user(field=OMIT) drops that key entirely


def build_user(_seed: int | None = None, **overrides) -> dict:
    rng = random.Random(_seed if _seed is not None else 42)
    n = rng.randint(1000, 99999)

    body = {
        "name": f"Test User {n}",
        "email": f"test.user.{n}@example.com",
        "gender": rng.choice(["male", "female"]),
        "status": rng.choice(["active", "inactive"]),
    }
    body.update(overrides)
    return {k: v for k, v in body.items() if v is not OMIT}
