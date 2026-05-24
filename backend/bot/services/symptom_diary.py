"""Symptom diary persistence + simple aggregations for trend charts.

Design choice: we key entries by ``cycle_code`` (the device-local
8-char identifier) so the diary works even for users who have not
paired with the Telegram bot. ``user_id`` is set opportunistically
when a paired user is found.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from typing import Iterable

from sqlalchemy import and_, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models import SymptomEntry
from bot.services.subscriptions import canonicalise_cycle_code


# Stable, UI-known symptom keys (a Settings-style allow-list). Anything
# else is rejected to keep the trend charts from accumulating typos.
ALLOWED_SYMPTOMS: tuple[str, ...] = (
    "cramps",      # «спазмы»
    "headache",    # «голова болит»
    "mood",        # «настроение» (1=плохо, 5=отлично)
    "energy",      # «энергия»
    "sleep",       # «сон»
    "appetite",    # «аппетит»
    "bloating",    # «вздутие»
    "acne",        # «высыпания»
    "libido",      # «либидо»
    "anxiety",     # «тревога»
)


class SymptomError(ValueError):
    """Raised for invalid inputs (bad cycle code, unknown symptom, etc.)."""


def _validate_intensity(value: int) -> int:
    if not isinstance(value, int):
        raise SymptomError("intensity must be an integer")
    if not 0 <= value <= 5:
        raise SymptomError("intensity must be between 0 and 5")
    return value


def _validate_symptom(name: str) -> str:
    if not name:
        raise SymptomError("symptom is required")
    norm = name.strip().lower()
    if norm not in ALLOWED_SYMPTOMS:
        raise SymptomError(
            f"unknown symptom '{name}'. allowed: {', '.join(ALLOWED_SYMPTOMS)}"
        )
    return norm


def _validate_cycle_code(raw: str) -> str:
    cleaned = canonicalise_cycle_code(raw)
    if not cleaned:
        raise SymptomError("invalid cycle_code")
    return cleaned


async def upsert_entry(
    session: AsyncSession,
    *,
    cycle_code: str,
    day: date,
    symptom: str,
    intensity: int,
    notes: str | None = None,
    user_id: int | None = None,
) -> SymptomEntry:
    """Insert a new entry OR update the row for the same (cycle_code, day, symptom).

    Symptoms are unique per day per cycle_code — re-submitting overrides
    intensity/notes without piling rows. This is what makes the trend
    chart honest (one data point per day per metric).
    """
    cycle_code = _validate_cycle_code(cycle_code)
    symptom = _validate_symptom(symptom)
    intensity = _validate_intensity(intensity)
    if notes is not None:
        notes = notes.strip()[:512] or None

    stmt = select(SymptomEntry).where(
        and_(
            SymptomEntry.cycle_code == cycle_code,
            SymptomEntry.day == day,
            SymptomEntry.symptom == symptom,
        )
    )
    row = (await session.execute(stmt)).scalar_one_or_none()
    if row is None:
        row = SymptomEntry(
            cycle_code=cycle_code,
            user_id=user_id,
            day=day,
            symptom=symptom,
            intensity=intensity,
            notes=notes,
        )
        session.add(row)
    else:
        row.intensity = intensity
        row.notes = notes
        if user_id is not None and row.user_id is None:
            row.user_id = user_id
    await session.flush()
    return row


async def delete_entry(
    session: AsyncSession,
    *,
    cycle_code: str,
    day: date,
    symptom: str,
) -> int:
    """Remove the row for that (cycle_code, day, symptom). Returns row count."""
    cycle_code = _validate_cycle_code(cycle_code)
    symptom = _validate_symptom(symptom)
    stmt = delete(SymptomEntry).where(
        and_(
            SymptomEntry.cycle_code == cycle_code,
            SymptomEntry.day == day,
            SymptomEntry.symptom == symptom,
        )
    )
    res = await session.execute(stmt)
    return int(res.rowcount or 0)


async def list_entries(
    session: AsyncSession,
    *,
    cycle_code: str,
    days_back: int = 90,
) -> list[SymptomEntry]:
    """Return entries from the last ``days_back`` days, newest first.

    ``days_back`` is clamped to a sane range (1..365) for safety.
    """
    cycle_code = _validate_cycle_code(cycle_code)
    days_back = max(1, min(int(days_back), 365))
    cutoff = date.today() - timedelta(days=days_back)
    stmt = (
        select(SymptomEntry)
        .where(
            and_(
                SymptomEntry.cycle_code == cycle_code,
                SymptomEntry.day >= cutoff,
            )
        )
        .order_by(SymptomEntry.day.desc(), SymptomEntry.symptom.asc())
    )
    rows = (await session.execute(stmt)).scalars().all()
    return list(rows)


def aggregate_for_chart(
    entries: Iterable[SymptomEntry],
    *,
    days_back: int,
    today: date | None = None,
) -> dict:
    """Pivot a flat list of entries into per-symptom day-series for charting.

    Output shape (JSON-ready):

    ```json
    {
      "labels": ["2026-04-01", "2026-04-02", ...],
      "series": {
        "cramps":   [0, 0, 3, 2, ...],
        "headache": [0, 1, 0, 0, ...],
        ...
      }
    }
    ```

    Days with no entry get 0 so the line stays continuous. We only emit a
    series for a symptom that actually has at least one non-zero day —
    keeps the chart readable for new users with sparse data.
    """
    if today is None:
        today = date.today()
    days_back = max(1, min(int(days_back), 365))
    start = today - timedelta(days=days_back - 1)
    labels: list[str] = [(start + timedelta(days=i)).isoformat() for i in range(days_back)]

    by_symptom: dict[str, dict[date, int]] = defaultdict(dict)
    for e in entries:
        if start <= e.day <= today:
            by_symptom[e.symptom][e.day] = int(e.intensity or 0)

    series: dict[str, list[int]] = {}
    for symptom, days_map in by_symptom.items():
        if not any(v > 0 for v in days_map.values()):
            continue
        series[symptom] = [days_map.get(start + timedelta(days=i), 0) for i in range(days_back)]

    return {"labels": labels, "series": series}
