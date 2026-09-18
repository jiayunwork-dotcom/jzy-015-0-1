"""Domain errors carried to the API layer as structured envelopes."""

from __future__ import annotations


class DomainError(Exception):
    """Base class for expected, client-visible failures."""

    def __init__(self, code: str, message: str, parameter: str | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.parameter = parameter

    def to_dict(self) -> dict:
        return {"code": self.code, "parameter": self.parameter, "message": self.message}


class InputValidationError(DomainError):
    """Missing, non-numeric, non-finite or non-positive input."""


class SteepnessLimitError(DomainError):
    """Height/depth ratio beyond the pinned linear-validity limit."""


class DispersionNotConvergedError(DomainError):
    """The iterative dispersion solve failed to close within tolerance."""
