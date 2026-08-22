"""Masks configured headers/query params/body paths and truncates oversized
bodies with an explicit marker. Applied BEFORE serialisation -- callers
(core.recorder) must run every value through here before it is turned into
JSON and written to disk, so raw secrets never reach the ledger regardless
of api_log_level.
"""
from __future__ import annotations

import json
from typing import Any, Iterable

MASK = "***REDACTED***"


def _mask_keys(obj: Any, redact_keys: frozenset[str]) -> Any:
    """Recursively mask any dict key (at any depth) whose lowercased name
    is in redact_keys -- covers headers, query params, and nested body
    fields (e.g. {"user": {"password": "..."}}) with one function.
    """
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if str(k).lower() in redact_keys:
                out[k] = MASK
            else:
                out[k] = _mask_keys(v, redact_keys)
        return out
    if isinstance(obj, list):
        return [_mask_keys(v, redact_keys) for v in obj]
    return obj


def redact_mapping(mapping: dict | None, redact_keys: Iterable[str]) -> dict:
    """For flat header/query-param dicts: mask values by key name only
    (no recursion needed -- headers/params are never nested)."""
    if not mapping:
        return {}
    keys = frozenset(k.lower() for k in redact_keys)
    return {k: (MASK if k.lower() in keys else v) for k, v in mapping.items()}


def truncate_text(text: str, max_chars: int) -> str:
    if text is None or len(text) <= max_chars:
        return text
    omitted = len(text) - max_chars
    return f"{text[:max_chars]} …[truncated {omitted} chars, api_max_body_chars={max_chars}]"


def prepare_body(body: Any, redact_keys: Iterable[str], max_body_chars: int) -> Any:
    """Mask secret fields in a request/response body, then cap its
    serialised size. Returns the masked structure unchanged if it fits
    under the cap, or a truncated string (with an explicit marker) if not.
    """
    if body is None:
        return None
    keys = frozenset(k.lower() for k in redact_keys)
    masked = _mask_keys(body, keys) if isinstance(body, (dict, list)) else body
    serialised = masked if isinstance(masked, str) else json.dumps(masked, default=str)
    if len(serialised) <= max_body_chars:
        return masked
    return truncate_text(serialised, max_body_chars)
