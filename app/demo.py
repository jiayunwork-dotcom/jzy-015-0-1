"""Built-in intermediate-depth swell demo case.

h = 10 m, T = 10 s, H = 1.5 m gives k·h ≈ 0.68 — clearly above the shallow
threshold (π/10 ≈ 0.314) and clearly below the deep threshold (π ≈ 3.14),
so the full dispersion relation is exercised.
"""

from __future__ import annotations

import math

from app.config import Settings
from app.constants import DEEP_WATER_KH, GRAVITY, SHALLOW_WATER_KH
from app.service import solve_sea_state
from app.validation import SeaState

DEMO_DEPTH = 10.0
DEMO_WAVE_HEIGHT = 1.5
DEMO_PERIOD = 10.0
DEMO_SEA_STATE = SeaState(depth=DEMO_DEPTH, wave_height=DEMO_WAVE_HEIGHT, period=DEMO_PERIOD)


def build_demo(settings: Settings) -> dict:
    solution = solve_sea_state(DEMO_SEA_STATE, settings)
    kin = solution.kinematics
    deep_phase_speed = GRAVITY * DEMO_PERIOD / math.tau
    deep_wavelength = GRAVITY * DEMO_PERIOD**2 / math.tau
    shallow_phase_speed = math.sqrt(GRAVITY * DEMO_DEPTH)
    phase_speed = kin.phase_speed
    checks = {
        "relative_depth_above_shallow_threshold": kin.relative_depth > SHALLOW_WATER_KH,
        "relative_depth_below_deep_threshold": kin.relative_depth < DEEP_WATER_KH,
        "full_dispersion_used": kin.regime == "intermediate",
        "phase_speed_below_deep_closed_form": phase_speed < deep_phase_speed,
        "phase_speed_below_shallow_closed_form": phase_speed < shallow_phase_speed,
        "group_speed_between_half_and_full_phase_speed": (
            0.5 * phase_speed < kin.group_speed < phase_speed
        ),
    }
    return {
        "description": "中等水深涌浪示范算例 — intermediate-depth swell solved with the full dispersion relation",
        "input": {
            "depth": DEMO_DEPTH,
            "wave_height": DEMO_WAVE_HEIGHT,
            "period": DEMO_PERIOD,
        },
        "solution": solution.to_dict(),
        "closed_form_reference": {
            "deep_water_phase_speed": deep_phase_speed,
            "deep_water_wavelength": deep_wavelength,
            "shallow_water_phase_speed": shallow_phase_speed,
        },
        "relative_depth_margins": {
            "above_shallow_threshold_by": kin.relative_depth - SHALLOW_WATER_KH,
            "below_deep_threshold_by": DEEP_WATER_KH - kin.relative_depth,
        },
        "checks": checks,
        "note": (
            "For any finite depth the true phase speed is strictly below both "
            "closed forms, because tanh(kh) < kh (c < √(g·h)) and tanh(kh) < 1 "
            "(c < g·T/2π); it only approaches them in the shallow/deep limits."
        ),
    }
