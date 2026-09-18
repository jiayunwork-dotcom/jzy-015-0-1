"""Physical and theoretical constants for the wave service.

``GRAVITY`` is the single source of truth for gravitational acceleration
across the whole service. No other module may define its own local value;
every module must import it from here.
"""

import math

# Standard gravity [m/s²], pinned service-wide.
GRAVITY: float = 9.80665

# Relative-water-depth (k·h) regime thresholds, fixed by linear wave theory.
#   k·h > π      → deep water
#   k·h < π/10   → shallow water
#   in between   → intermediate depth (full dispersion, no closed-form shortcut)
DEEP_WATER_KH: float = math.pi
SHALLOW_WATER_KH: float = math.pi / 10.0
