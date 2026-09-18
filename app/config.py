"""Runtime configuration.

Physics constants (gravity, regime thresholds) live in :mod:`app.constants`;
this module only holds tunable service settings. Everything here is echoed
back by the ``/api/config`` endpoint.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="WAVE_")

    # Persistence.
    database_url: str = "postgresql+asyncpg://wave:wave@localhost:5432/wavedb"

    # Linear-theory validity limit on the height/depth ratio H/h.
    max_height_depth_ratio: float = 0.2

    # Pinned root-finding tolerance and iteration budget for the dispersion solve.
    solver_tolerance: float = 1e-12
    solver_max_iterations: int = 100

    # Request guard rails.
    max_batch_size: int = 500
    max_grid_points: int = 512
    max_grid_cells: int = 65536


@lru_cache
def get_settings() -> Settings:
    return Settings()
