"""Framework-wide exception types.

VerificationError subclasses AssertionError deliberately: pytest's assertion
rewriting/formatting machinery keys off AssertionError, so a verification
failure raised by core.assertions still renders as a normal pytest failure
(red, with a clean message) rather than an unhandled-error traceback.
"""
from __future__ import annotations


class ConfigError(Exception):
    """Raised at collection time when pytest.ini / env vars fail validation."""


class TransportError(Exception):
    """Raised when a request exhausts its retry budget without a response."""


class VerificationError(AssertionError):
    """Raised by core.assertions after the failing check has been recorded."""
