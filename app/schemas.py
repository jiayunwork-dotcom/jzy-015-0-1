"""Pydantic request/response schemas for the HTTP layer.

Sea-state fields are typed as ``Any`` on purpose: the service performs its
own strict validation (see :mod:`app.validation`) so that single and batch
endpoints share one validation path and one error-envelope format.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SolvePayload(BaseModel):
    depth: Any = Field(..., description="Water depth h [m], must be a positive finite number")
    wave_height: Any = Field(
        ..., description="Wave height H [m], must be a positive finite number"
    )
    period: Any = Field(..., description="Wave period T [s], must be a positive finite number")
    positions: list[Any] | None = Field(
        None, description="Optional x positions [m]; together with 'times' yields an elevation grid"
    )
    times: list[Any] | None = Field(
        None, description="Optional times t [s]; together with 'positions' yields an elevation grid"
    )


class BatchPayload(BaseModel):
    items: list[Any] = Field(
        ...,
        min_length=1,
        description="Sea-state items, each an object with depth, wave_height, period",
    )


class ElevationGrid(BaseModel):
    positions: list[float]
    times: list[float]
    values: list[list[float]]


class SolutionResponse(BaseModel):
    input: dict[str, float]
    angular_frequency: float
    wave_number: float
    wavelength: float
    phase_speed: float
    group_speed: float
    relative_depth: float
    regime: str
    height_depth_ratio: float
    elevation: ElevationGrid | None = None


class ConfigResponse(BaseModel):
    gravity: float
    deep_water_kh_threshold: float
    shallow_water_kh_threshold: float
    max_height_depth_ratio: float
    solver_tolerance: float
    solver_max_iterations: int
    max_batch_size: int
    max_grid_points: int
    max_grid_cells: int
