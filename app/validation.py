"""Input validation shared by the single and batch endpoints.

Every failure raises a :class:`DomainError` carrying a stable ``code`` and
the offending ``parameter`` so the API layer can point at exactly which
field of which item went wrong.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from app.errors import InputValidationError, SteepnessLimitError

REQUIRED_FIELDS = ("depth", "wave_height", "period")


@dataclass(frozen=True)
class SeaState:
    """One validated sea state: water depth h [m], wave height H [m], period T [s]."""

    depth: float
    wave_height: float
    period: float


def validate_sea_state_mapping(data: Any) -> SeaState:
    """Validate a raw JSON mapping into a :class:`SeaState`.

    Rejects: non-object items, missing fields, non-numeric values (booleans
    included), non-finite values (NaN/±inf) and non-positive values.
    """
    if not isinstance(data, dict):
        raise InputValidationError(
            "invalid_item",
            "sea-state item must be a JSON object with depth, wave_height and period",
        )
    values: dict[str, float] = {}
    for name in REQUIRED_FIELDS:
        if name not in data:
            raise InputValidationError(
                "missing_field", f"missing required field '{name}'", parameter=name
            )
        raw = data[name]
        if isinstance(raw, bool) or not isinstance(raw, (int, float)):
            raise InputValidationError(
                "invalid_parameter", f"'{name}' must be a number", parameter=name
            )
        value = float(raw)
        if not math.isfinite(value):
            raise InputValidationError(
                "non_finite", f"'{name}' must be a finite number", parameter=name
            )
        if value <= 0.0:
            raise InputValidationError(
                "not_positive", f"'{name}' must be positive, got {value}", parameter=name
            )
        values[name] = value
    return SeaState(**values)


def check_linear_validity(sea_state: SeaState, max_height_depth_ratio: float) -> float:
    """Return H/h, rejecting sea states beyond the pinned linear-validity limit."""
    ratio = sea_state.wave_height / sea_state.depth
    if ratio > max_height_depth_ratio:
        raise SteepnessLimitError(
            "steepness_limit_exceeded",
            f"height/depth ratio {ratio:.4f} exceeds the linear validity limit "
            f"{max_height_depth_ratio}",
            parameter="wave_height",
        )
    return ratio


def validate_grid_axis(values: Any, name: str, max_points: int) -> list[float]:
    """Validate one elevation-grid axis (positions or times)."""
    if not isinstance(values, list) or not values:
        raise InputValidationError(
            "invalid_parameter",
            f"'{name}' must be a non-empty array of numbers",
            parameter=name,
        )
    if len(values) > max_points:
        raise InputValidationError(
            "grid_too_large",
            f"'{name}' has {len(values)} points; the limit is {max_points}",
            parameter=name,
        )
    axis: list[float] = []
    for value in values:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise InputValidationError(
                "invalid_parameter", f"'{name}' points must be numbers", parameter=name
            )
        point = float(value)
        if not math.isfinite(point):
            raise InputValidationError(
                "non_finite", f"'{name}' points must be finite numbers", parameter=name
            )
        axis.append(point)
    return axis
