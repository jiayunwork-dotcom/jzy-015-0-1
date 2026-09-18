"""Surface elevation: η(x, t) = (H/2)·cos(k·x − ω·t)."""

import math

import pytest

from app.elevation import elevation_grid, surface_elevation

H = 1.6
K = 0.0680821
OMEGA = 0.6283185


def elev(x, t):
    return surface_elevation(
        wave_height=H, wave_number=K, angular_frequency=OMEGA, position=x, time=t
    )


def test_elevation_at_origin_is_half_height():
    assert elev(0.0, 0.0) == pytest.approx(0.5 * H)


def test_phase_convention():
    x, t = 12.3, 4.5
    assert elev(x, t) == pytest.approx(0.5 * H * math.cos(K * x - OMEGA * t))


def test_spatial_and_temporal_periodicity():
    x, t = 3.1, 2.2
    wavelength = math.tau / K
    period = math.tau / OMEGA
    assert elev(x + wavelength, t) == pytest.approx(elev(x, t))
    assert elev(x, t + period) == pytest.approx(elev(x, t))


def test_elevation_grid_shape_and_values():
    positions = [0.0, 10.0, 20.0]
    times = [0.0, 1.0]
    grid = elevation_grid(
        wave_height=H,
        wave_number=K,
        angular_frequency=OMEGA,
        positions=positions,
        times=times,
    )
    assert len(grid) == len(positions)
    assert all(len(row) == len(times) for row in grid)
    assert grid[0][0] == pytest.approx(0.5 * H)
    for i, x in enumerate(positions):
        for j, t in enumerate(times):
            assert grid[i][j] == pytest.approx(elev(x, t))
