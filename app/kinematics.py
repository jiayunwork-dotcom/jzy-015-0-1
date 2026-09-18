"""Derived wave kinematics.

Every quantity here consumes the *single* wave number produced by the
dispersion solve — nothing re-solves the dispersion relation downstream.

    wavelength   L  = 2π / k
    phase speed  c  = ω / k
    group speed  cg = (c / 2) · (1 + 2kh / sinh(2kh))

The sinh correction is mandatory: dropping it (cg ≡ c/2) is an
implementation error. In deep water the bracket tends to 1 (cg → c/2);
in shallow water it tends to 2 (cg → c).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from app.constants import DEEP_WATER_KH, SHALLOW_WATER_KH

REGIME_DEEP = "deep"
REGIME_SHALLOW = "shallow"
REGIME_INTERMEDIATE = "intermediate"

# Beyond 2·k·h ≈ 40 the ratio 2kh/sinh(2kh) is below 4e-16 (and sinh would
# eventually overflow float64), so the correction is taken as exactly zero.
_SINH_CORRECTION_CUTOFF = 40.0


def classify_regime(relative_depth: float) -> str:
    """Classify by k·h: > π deep, < π/10 shallow, otherwise intermediate."""
    if relative_depth > DEEP_WATER_KH:
        return REGIME_DEEP
    if relative_depth < SHALLOW_WATER_KH:
        return REGIME_SHALLOW
    return REGIME_INTERMEDIATE


@dataclass(frozen=True)
class Kinematics:
    wave_number: float
    wavelength: float
    phase_speed: float
    group_speed: float
    relative_depth: float
    regime: str


def compute_kinematics(
    *,
    angular_frequency: float,
    wave_number: float,
    depth: float,
) -> Kinematics:
    k = wave_number
    kh = k * depth
    wavelength = math.tau / k
    phase_speed = angular_frequency / k
    two_kh = 2.0 * kh
    correction = 0.0 if two_kh > _SINH_CORRECTION_CUTOFF else two_kh / math.sinh(two_kh)
    group_speed = 0.5 * phase_speed * (1.0 + correction)
    return Kinematics(
        wave_number=k,
        wavelength=wavelength,
        phase_speed=phase_speed,
        group_speed=group_speed,
        relative_depth=kh,
        regime=classify_regime(kh),
    )
