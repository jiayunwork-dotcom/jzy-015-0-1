"""Sea-state solving: validation → dispersion → kinematics, one wave number."""

from __future__ import annotations

import math
from dataclasses import dataclass

from app.config import Settings
from app.dispersion import solve_wavenumber
from app.kinematics import Kinematics, compute_kinematics
from app.validation import SeaState, check_linear_validity


@dataclass(frozen=True)
class SeaStateSolution:
    sea_state: SeaState
    angular_frequency: float
    kinematics: Kinematics
    height_depth_ratio: float

    def to_dict(self) -> dict:
        kin = self.kinematics
        return {
            "input": {
                "depth": self.sea_state.depth,
                "wave_height": self.sea_state.wave_height,
                "period": self.sea_state.period,
            },
            "angular_frequency": self.angular_frequency,
            "wave_number": kin.wave_number,
            "wavelength": kin.wavelength,
            "phase_speed": kin.phase_speed,
            "group_speed": kin.group_speed,
            "relative_depth": kin.relative_depth,
            "regime": kin.regime,
            "height_depth_ratio": self.height_depth_ratio,
        }


def solve_sea_state(sea_state: SeaState, settings: Settings) -> SeaStateSolution:
    """Solve one sea state with linear wave theory.

    The full dispersion relation is always solved iteratively — intermediate
    depths never fall back to a deep- or shallow-water closed form. All
    derived quantities share the resulting single wave number.
    """
    ratio = check_linear_validity(sea_state, settings.max_height_depth_ratio)
    angular_frequency = math.tau / sea_state.period
    wave_number = solve_wavenumber(
        angular_frequency=angular_frequency,
        depth=sea_state.depth,
        tolerance=settings.solver_tolerance,
        max_iterations=settings.solver_max_iterations,
    )
    kinematics = compute_kinematics(
        angular_frequency=angular_frequency,
        wave_number=wave_number,
        depth=sea_state.depth,
    )
    return SeaStateSolution(
        sea_state=sea_state,
        angular_frequency=angular_frequency,
        kinematics=kinematics,
        height_depth_ratio=ratio,
    )
