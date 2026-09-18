"""Kinematics: deep/shallow closed-form limits, intermediate full dispersion,
and the scaling laws used to judge the implementation."""

import math

import pytest

from app.config import Settings
from app.constants import GRAVITY
from app.elevation import surface_elevation
from app.service import solve_sea_state
from app.validation import SeaState

SETTINGS = Settings()


def solve(depth, wave_height, period):
    return solve_sea_state(
        SeaState(depth=depth, wave_height=wave_height, period=period), SETTINGS
    )


def test_deep_water_phase_speed_matches_closed_form():
    period = 10.0
    sol = solve(depth=5000.0, wave_height=1.0, period=period)
    kin = sol.kinematics
    assert kin.regime == "deep"
    assert kin.relative_depth > math.pi
    # c → g·T / 2π and L → g·T² / 2π
    assert kin.phase_speed == pytest.approx(GRAVITY * period / math.tau, rel=1e-9)
    assert kin.wavelength == pytest.approx(GRAVITY * period**2 / math.tau, rel=1e-9)
    # deep-water group speed tends to half the phase speed
    assert kin.group_speed == pytest.approx(0.5 * kin.phase_speed, rel=1e-9)


def test_shallow_water_phase_speed_matches_closed_form():
    depth = 0.1
    sol = solve(depth=depth, wave_height=0.005, period=30.0)
    kin = sol.kinematics
    assert kin.regime == "shallow"
    assert kin.relative_depth < math.pi / 10
    # c → √(g·h)
    assert kin.phase_speed == pytest.approx(math.sqrt(GRAVITY * depth), rel=1e-3)
    # shallow-water group speed tends to the phase speed
    assert kin.group_speed == pytest.approx(kin.phase_speed, rel=1e-3)


def test_intermediate_depth_uses_full_dispersion():
    depth, period = 10.0, 10.0
    sol = solve(depth=depth, wave_height=1.5, period=period)
    kin = sol.kinematics
    assert kin.regime == "intermediate"
    # clearly inside the intermediate band, not hugging either threshold
    assert kin.relative_depth > 1.5 * math.pi / 10
    assert kin.relative_depth < 0.5 * math.pi
    # the full dispersion relation holds (not a closed-form shortcut)
    omega = sol.angular_frequency
    residual = omega**2 - GRAVITY * kin.wave_number * math.tanh(kin.relative_depth)
    assert abs(residual) < 1e-10 * omega**2
    # For any finite depth the true phase speed is strictly bounded above by
    # BOTH closed forms, because tanh(kh) < kh (c < √(g·h)) and tanh(kh) < 1
    # (c < g·T/2π); it approaches each only in its limit.
    shallow_closed = math.sqrt(GRAVITY * depth)
    deep_closed = GRAVITY * period / math.tau
    assert 0.0 < kin.phase_speed < shallow_closed < deep_closed


def test_group_speed_sinh_correction():
    sol = solve(depth=10.0, wave_height=1.5, period=10.0)
    kin = sol.kinematics
    kh = kin.relative_depth
    expected = 0.5 * kin.phase_speed * (1.0 + 2.0 * kh / math.sinh(2.0 * kh))
    assert kin.group_speed == pytest.approx(expected, rel=1e-12)
    assert 0.5 * kin.phase_speed < kin.group_speed < kin.phase_speed


def test_deep_water_period_doubling_quadruples_wavelength():
    s1 = solve(depth=5000.0, wave_height=1.0, period=10.0)
    s2 = solve(depth=5000.0, wave_height=1.0, period=20.0)
    assert s2.kinematics.wavelength / s1.kinematics.wavelength == pytest.approx(4.0, rel=1e-9)
    assert s2.kinematics.phase_speed / s1.kinematics.phase_speed == pytest.approx(2.0, rel=1e-9)


def test_deep_water_phase_speed_saturates_with_depth():
    s1 = solve(depth=1000.0, wave_height=1.0, period=10.0)
    s2 = solve(depth=5000.0, wave_height=1.0, period=10.0)
    assert s1.kinematics.regime == s2.kinematics.regime == "deep"
    assert s2.kinematics.phase_speed >= s1.kinematics.phase_speed
    relative_growth = (
        s2.kinematics.phase_speed - s1.kinematics.phase_speed
    ) / s1.kinematics.phase_speed
    assert relative_growth < 1e-6


def test_shallow_water_depth_quadruple_doubles_phase_speed():
    s1 = solve(depth=0.1, wave_height=0.005, period=30.0)
    s2 = solve(depth=0.4, wave_height=0.005, period=30.0)
    assert s1.kinematics.regime == s2.kinematics.regime == "shallow"
    assert s2.kinematics.phase_speed / s1.kinematics.phase_speed == pytest.approx(2.0, rel=1e-3)


def test_wave_height_doubling_scales_elevation_only():
    s1 = solve(depth=10.0, wave_height=0.8, period=10.0)
    s2 = solve(depth=10.0, wave_height=1.6, period=10.0)
    # wave number, phase speed and group speed are unchanged
    assert s1.kinematics.wave_number == s2.kinematics.wave_number
    assert s1.kinematics.phase_speed == s2.kinematics.phase_speed
    assert s1.kinematics.group_speed == s2.kinematics.group_speed
    # only the surface elevation scales, by exactly the height ratio
    for x, t in [(0.0, 0.0), (3.0, 2.0), (17.5, 6.3)]:
        e1 = surface_elevation(
            wave_height=0.8,
            wave_number=s1.kinematics.wave_number,
            angular_frequency=s1.angular_frequency,
            position=x,
            time=t,
        )
        e2 = surface_elevation(
            wave_height=1.6,
            wave_number=s2.kinematics.wave_number,
            angular_frequency=s2.angular_frequency,
            position=x,
            time=t,
        )
        assert e2 == pytest.approx(2.0 * e1, rel=1e-12)
