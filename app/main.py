"""HTTP API for the linear gravity-wave dispersion service.

Endpoints
---------
POST /api/solve    solve one sea state (optional position×time elevation grid)
POST /api/batch    solve a batch; per-item errors never fail the whole batch
GET  /api/history  query persisted calculations
GET  /api/config   echo gravity, regime thresholds, linear limit, solver tolerance
GET  /api/health   runtime status for monitoring
GET  /api/demo     built-in intermediate-depth swell demo case
"""

from __future__ import annotations

import time
import uuid
from contextlib import asynccontextmanager
from typing import Any, Literal

from fastapi import Depends, FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.config import Settings, get_settings
from app.constants import DEEP_WATER_KH, GRAVITY, SHALLOW_WATER_KH
from app.db import create_engine_for_url, init_models
from app.demo import build_demo
from app.elevation import elevation_grid
from app.errors import DomainError, InputValidationError
from app.persistence import query_history, record_to_dict, save_calculation
from app.schemas import BatchPayload, ConfigResponse, SolutionResponse, SolvePayload
from app.service import solve_sea_state
from app.validation import validate_grid_axis, validate_sea_state_mapping

VERSION = "1.0.0"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await init_models(app.state.engine)
        yield
        await app.state.engine.dispose()

    app = FastAPI(
        title="Linear Gravity Wave Dispersion Service",
        version=VERSION,
        lifespan=lifespan,
        summary="Solve the linear gravity-wave dispersion relation for sea states.",
    )
    app.state.settings = settings
    app.state.engine = create_engine_for_url(settings.database_url)
    app.state.session_factory = async_sessionmaker(app.state.engine, expire_on_commit=False)
    app.state.started_at = time.monotonic()

    def get_config(request: Request) -> Settings:
        return request.app.state.settings

    async def get_session(request: Request):
        async with request.app.state.session_factory() as session:
            yield session

    @app.exception_handler(DomainError)
    async def domain_error_handler(_request: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"error": exc.to_dict()})

    @app.exception_handler(RequestValidationError)
    async def request_validation_handler(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        errors = exc.errors()
        first = errors[0] if errors else {}
        loc = [part for part in first.get("loc", []) if part != "body"]
        parameter = str(loc[-1]) if loc else None
        code = "missing_field" if first.get("type") == "missing" else "invalid_parameter"
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": code,
                    "parameter": parameter,
                    "message": first.get("msg", "invalid request"),
                }
            },
        )

    @app.get("/")
    async def root() -> dict:
        return {
            "service": "linear-gravity-wave-dispersion",
            "version": VERSION,
            "docs": "/docs",
            "endpoints": {
                "solve": "POST /api/solve",
                "batch": "POST /api/batch",
                "history": "GET /api/history",
                "config": "GET /api/config",
                "health": "GET /api/health",
                "demo": "GET /api/demo",
            },
        }

    @app.post("/api/solve", response_model=SolutionResponse)
    async def solve_single(
        payload: SolvePayload,
        session=Depends(get_session),
        config: Settings = Depends(get_config),
    ) -> dict:
        sea_state = validate_sea_state_mapping(
            {
                "depth": payload.depth,
                "wave_height": payload.wave_height,
                "period": payload.period,
            }
        )
        solution = solve_sea_state(sea_state, config)
        result = solution.to_dict()
        if (payload.positions is None) != (payload.times is None):
            missing = "times" if payload.positions is not None else "positions"
            raise InputValidationError(
                "invalid_parameter",
                "'positions' and 'times' must be provided together",
                parameter=missing,
            )
        if payload.positions is not None and payload.times is not None:
            positions = validate_grid_axis(payload.positions, "positions", config.max_grid_points)
            times = validate_grid_axis(payload.times, "times", config.max_grid_points)
            if len(positions) * len(times) > config.max_grid_cells:
                raise InputValidationError(
                    "grid_too_large",
                    f"elevation grid {len(positions)}x{len(times)} exceeds the "
                    f"{config.max_grid_cells}-cell limit",
                    parameter="positions",
                )
            result["elevation"] = {
                "positions": positions,
                "times": times,
                "values": elevation_grid(
                    wave_height=sea_state.wave_height,
                    wave_number=solution.kinematics.wave_number,
                    angular_frequency=solution.angular_frequency,
                    positions=positions,
                    times=times,
                ),
            }
        await save_calculation(session, kind="single", input_data=result["input"], result=result)
        await session.commit()
        return result

    @app.post("/api/batch")
    async def solve_batch(
        payload: BatchPayload,
        session=Depends(get_session),
        config: Settings = Depends(get_config),
    ) -> dict:
        if len(payload.items) > config.max_batch_size:
            raise InputValidationError(
                "batch_too_large",
                f"batch has {len(payload.items)} items; the limit is {config.max_batch_size}",
                parameter="items",
            )
        batch_id = uuid.uuid4().hex
        results: list[dict[str, Any]] = []
        succeeded = 0
        for index, item in enumerate(payload.items):
            try:
                sea_state = validate_sea_state_mapping(item)
                solution = solve_sea_state(sea_state, config)
                solved = solution.to_dict()
                results.append({"index": index, "ok": True, "solution": solved})
                await save_calculation(
                    session,
                    kind="batch",
                    batch_id=batch_id,
                    item_index=index,
                    input_data=solved["input"],
                    result=solved,
                )
                succeeded += 1
            except DomainError as exc:
                # One bad item must not fail the batch: report index + parameter
                # and keep solving the remaining items.
                error = exc.to_dict()
                results.append({"index": index, "ok": False, "error": error})
                await save_calculation(
                    session,
                    kind="batch",
                    batch_id=batch_id,
                    item_index=index,
                    input_data=item if isinstance(item, dict) else {"raw": item},
                    error=error,
                )
        await session.commit()
        return {
            "batch_id": batch_id,
            "total": len(payload.items),
            "succeeded": succeeded,
            "failed": len(payload.items) - succeeded,
            "results": results,
        }

    @app.get("/api/history")
    async def history(
        session=Depends(get_session),
        regime: Literal["deep", "shallow", "intermediate"] | None = None,
        ok: bool | None = None,
        kind: Literal["single", "batch", "demo"] | None = None,
        batch_id: str | None = None,
        min_period: float | None = None,
        max_period: float | None = None,
        min_depth: float | None = None,
        max_depth: float | None = None,
        limit: int = Query(50, ge=1, le=500),
        offset: int = Query(0, ge=0),
    ) -> dict:
        total, records = await query_history(
            session,
            regime=regime,
            ok=ok,
            kind=kind,
            batch_id=batch_id,
            min_period=min_period,
            max_period=max_period,
            min_depth=min_depth,
            max_depth=max_depth,
            limit=limit,
            offset=offset,
        )
        return {"total": total, "items": [record_to_dict(record) for record in records]}

    @app.get("/api/config", response_model=ConfigResponse)
    async def config_echo(config: Settings = Depends(get_config)) -> ConfigResponse:
        return ConfigResponse(
            gravity=GRAVITY,
            deep_water_kh_threshold=DEEP_WATER_KH,
            shallow_water_kh_threshold=SHALLOW_WATER_KH,
            max_height_depth_ratio=config.max_height_depth_ratio,
            solver_tolerance=config.solver_tolerance,
            solver_max_iterations=config.solver_max_iterations,
            max_batch_size=config.max_batch_size,
            max_grid_points=config.max_grid_points,
            max_grid_cells=config.max_grid_cells,
        )

    @app.get("/api/health")
    async def health(request: Request) -> JSONResponse:
        database = "down"
        try:
            async with request.app.state.session_factory() as session:
                await session.execute(select(1))
            database = "up"
        except Exception:
            database = "down"
        healthy = database == "up"
        return JSONResponse(
            status_code=200 if healthy else 503,
            content={
                "status": "ok" if healthy else "degraded",
                "database": database,
                "version": VERSION,
                "uptime_seconds": round(time.monotonic() - request.app.state.started_at, 3),
            },
        )

    @app.get("/api/demo")
    async def demo(
        session=Depends(get_session), config: Settings = Depends(get_config)
    ) -> dict:
        payload = build_demo(config)
        await save_calculation(
            session, kind="demo", input_data=payload["input"], result=payload["solution"]
        )
        await session.commit()
        return payload

    return app


app = create_app()
