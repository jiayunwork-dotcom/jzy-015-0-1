"""Dispersion root-finding: ω² = g·k·tanh(k·h) solved iteratively."""

import math

import pytest

from app.constants import GRAVITY
from app.dispersion import solve_wavenumber
from app.errors import DispersionNotConvergedError

TOLERANCE = 1e-12
MAX_ITERATIONS = 100


def solve_k(depth, period):
    return solve_wavenumber(
        angular_frequency=math.tau / period,
        depth=depth,
        tolerance=TOLERANCE,
        max_iterations=MAX_ITERATIONS,
    )


@pytest.mark.parametrize(
    "depth,period",
    [
        (0.1, 30.0),  # shallow
        (1.0, 5.0),
        (10.0, 10.0),  # intermediate (demo case)
        (50.0, 12.0),
        (5000.0, 10.0),  # deep
        (2.0, 2.5),
    ],
)
def test_solution_satisfies_dispersion_residual(depth, period):
    k = solve_k(depth, period)
    omega = math.tau / period
    residual = omega**2 - GRAVITY * k * math.tanh(k * depth)
    assert abs(residual) <= 1e-9 * omega**2


def test_deep_limit_wavenumber():
    period = 10.0
    omega = math.tau / period
    k = solve_k(5000.0, period)
    assert k == pytest.approx(omega**2 / GRAVITY, rel=1e-9)


def test_shallow_limit_wavenumber():
    depth, period = 0.1, 30.0
    omega = math.tau / period
    k = solve_k(depth, period)
    assert k == pytest.approx(omega / math.sqrt(GRAVITY * depth), rel=1e-3)


def test_non_convergence_is_an_error():
    with pytest.raises(DispersionNotConvergedError):
        solve_wavenumber(
            angular_frequency=1.0,
            depth=10.0,
            tolerance=TOLERANCE,
            max_iterations=0,
        )


def test_solver_is_deterministic():
    assert solve_k(10.0, 10.0) == solve_k(10.0, 10.0)
