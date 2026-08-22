"""Contracts for gorest.in's /v2/users resource, as pydantic models --
plain Python objects, not JSON files. SCHEMAS is what core.schemas.
SchemaRegistry indexes: {name: model} pairs, used as
assert_schema(resp, name).
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr


class User(BaseModel):
    """A single user, as returned by GET/POST/PUT /v2/users(/{id})."""

    model_config = ConfigDict(extra="forbid")  # unexpected fields = drift

    id: int
    name: str
    email: EmailStr
    gender: Literal["male", "female"]
    status: Literal["active", "inactive"]


class ValidationErrorItem(BaseModel):
    """One entry of gorest's 422 response, which is a JSON array of these
    -- see "validation_error" below for the array shape itself."""

    model_config = ConfigDict(extra="forbid")

    field: str
    message: str


SCHEMAS = {
    "user": User,
    "users_list": list[User],
    "validation_error": list[ValidationErrorItem],
}
