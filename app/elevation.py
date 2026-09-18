"""Surface-elevation reconstruction.

Phase convention, uniform across the whole service:

    η(x, t) = (H / 2) · cos(k·x − ω·t)
"""

from __future__ import annotations

import math


def surface_elevation(
    *,
    wave_height: float,
    wave_number: float,
    angular_frequency: float,
    position: float,
    time: float,
) -> float:
    """η at one horizontal position ``x`` [m] and time ``t`` [s]."""
    return 0.5 * wave_height * math.cos(wave_number * position - angular_frequency * time)


def elevation_grid(
    *,
    wave_height: float,
    wave_number: float,
    angular_frequency: float,
    positions: list[float],
    times: list[float],
) -> list[list[float]]:
    """η over a position×time grid; ``result[i][j] = η(positions[i], times[j])``."""
    return [
        [
            surface_elevation(
                wave_height=wave_height,
                wave_number=wave_number,
                angular_frequency=angular_frequency,
                position=x,
                time=t,
            )
            for t in times
        ]
        for x in positions
    ]
