"""Iterative inversion of the linear gravity-wave dispersion relation.

    ω² = g · k · tanh(k · h)

The equation is implicit in the wave number ``k`` and is solved by
Newton–Raphson iteration on the dimensionless relative depth ``y = k·h``,
which rewrites the relation as

    y · tanh(y) = ω² · h / g

The iteration must close within the pinned tolerance; otherwise the solve is
rejected as an error instead of returning an unconverged number. Note the
hyperbolic tangent — using the ordinary tangent here would be a bug.
"""

import math

from app.constants import GRAVITY
from app.errors import DispersionNotConvergedError


def solve_wavenumber(
    *,
    angular_frequency: float,
    depth: float,
    tolerance: float,
    max_iterations: int,
) -> float:
    """Return the wave number ``k`` [rad/m] for ``ω`` [rad/s] and depth ``h`` [m].

    Raises:
        DispersionNotConvergedError: if the iteration does not close within
            ``max_iterations`` steps at the pinned ``tolerance``.
        ValueError: on non-positive solver inputs (a programming error; HTTP
            inputs are validated upstream).
    """
    if angular_frequency <= 0.0:
        raise ValueError("angular_frequency must be positive")
    if depth <= 0.0:
        raise ValueError("depth must be positive")
    if tolerance <= 0.0:
        raise ValueError("tolerance must be positive")

    mu = angular_frequency * angular_frequency * depth / GRAVITY
    # Initial guess: shallow-water root y ≈ √μ for μ < 1, deep-water root
    # y ≈ μ otherwise. Newton converges monotonically from either side here.
    y = math.sqrt(mu) if mu < 1.0 else mu
    for _ in range(max_iterations):
        t = math.tanh(y)
        residual = y * t - mu
        # d/dy [y·tanh(y)] = tanh(y) + y·sech²(y), with sech² = 1 − tanh².
        derivative = t + y * (1.0 - t * t)
        step = residual / derivative
        y -= step
        if abs(step) <= tolerance * max(1.0, abs(y)):
            return y / depth
    raise DispersionNotConvergedError(
        code="dispersion_not_converged",
        message=(
            "dispersion relation failed to close within "
            f"{max_iterations} iterations at tolerance {tolerance}"
        ),
    )
