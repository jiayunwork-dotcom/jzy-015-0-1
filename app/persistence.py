"""Persistence: every calculation is stored with its inputs and results."""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    Float,
    Integer,
    String,
    func,
    select,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base

JsonType = JSON().with_variant(JSONB, "postgresql")


class CalculationRecord(Base):
    __tablename__ = "calculation_records"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True
    )
    kind: Mapped[str] = mapped_column(String(16), index=True)  # single | batch | demo
    batch_id: Mapped[str | None] = mapped_column(String(36), index=True)
    item_index: Mapped[int | None] = mapped_column(Integer)
    ok: Mapped[bool] = mapped_column(Boolean, index=True)
    regime: Mapped[str | None] = mapped_column(String(16), index=True)
    depth: Mapped[float | None] = mapped_column(Float, index=True)
    wave_height: Mapped[float | None] = mapped_column(Float)
    period: Mapped[float | None] = mapped_column(Float, index=True)
    input_json: Mapped[dict[str, Any]] = mapped_column(JsonType)
    result_json: Mapped[dict[str, Any] | None] = mapped_column(JsonType)
    error_json: Mapped[dict[str, Any] | None] = mapped_column(JsonType)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )


def _finite_float(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    result = float(value)
    return result if math.isfinite(result) else None


async def save_calculation(
    session: AsyncSession,
    *,
    kind: str,
    input_data: dict,
    batch_id: str | None = None,
    item_index: int | None = None,
    result: dict | None = None,
    error: dict | None = None,
) -> CalculationRecord:
    record = CalculationRecord(
        kind=kind,
        batch_id=batch_id,
        item_index=item_index,
        ok=error is None,
        regime=(result or {}).get("regime"),
        depth=_finite_float(input_data.get("depth")),
        wave_height=_finite_float(input_data.get("wave_height")),
        period=_finite_float(input_data.get("period")),
        input_json=input_data,
        result_json=result,
        error_json=error,
    )
    session.add(record)
    await session.flush()
    return record


async def query_history(
    session: AsyncSession,
    *,
    regime: str | None = None,
    ok: bool | None = None,
    kind: str | None = None,
    batch_id: str | None = None,
    min_period: float | None = None,
    max_period: float | None = None,
    min_depth: float | None = None,
    max_depth: float | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[int, list[CalculationRecord]]:
    conditions = []
    if regime is not None:
        conditions.append(CalculationRecord.regime == regime)
    if ok is not None:
        conditions.append(CalculationRecord.ok.is_(ok))
    if kind is not None:
        conditions.append(CalculationRecord.kind == kind)
    if batch_id is not None:
        conditions.append(CalculationRecord.batch_id == batch_id)
    if min_period is not None:
        conditions.append(CalculationRecord.period >= min_period)
    if max_period is not None:
        conditions.append(CalculationRecord.period <= max_period)
    if min_depth is not None:
        conditions.append(CalculationRecord.depth >= min_depth)
    if max_depth is not None:
        conditions.append(CalculationRecord.depth <= max_depth)

    total = (
        await session.execute(
            select(func.count()).select_from(CalculationRecord).where(*conditions)
        )
    ).scalar_one()
    rows = (
        (
            await session.execute(
                select(CalculationRecord)
                .where(*conditions)
                .order_by(CalculationRecord.id.desc())
                .limit(limit)
                .offset(offset)
            )
        )
        .scalars()
        .all()
    )
    return total, list(rows)


def record_to_dict(record: CalculationRecord) -> dict:
    return {
        "id": record.id,
        "kind": record.kind,
        "batch_id": record.batch_id,
        "item_index": record.item_index,
        "ok": record.ok,
        "regime": record.regime,
        "input": record.input_json,
        "result": record.result_json,
        "error": record.error_json,
        "created_at": record.created_at.isoformat() if record.created_at else None,
    }
