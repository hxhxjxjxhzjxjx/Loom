"""Cycle-forecast persistence.

Replaces the legacy ``cycle_sync_code`` plumbing: instead of asking the
user to copy a base32 code from the app and paste ``/sync <code>`` into
the bot, the app now POSTs the next ``N`` cycles' dates through
``POST /v1/pair/<token>/forecast`` once it has paired Telegram. We wipe
the user's existing forecast on every push so there is at most one
"current truth" set on disk.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone

from sqlalchemy import asc, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models import CycleForecast, User


@dataclass(slots=True)
class ForecastEntry:
    """Plain DTO for one projected cycle."""

    cycle_start: date
    period_end: date
    ovulation: date
    fertile_start: date
    fertile_end: date


async def replace_user_forecast(
    session: AsyncSession,
    user: User,
    entries: list[ForecastEntry],
) -> int:
    """Drop any existing forecast rows for ``user`` and insert ``entries``.

    Returns the number of rows inserted.
    """
    await session.execute(
        delete(CycleForecast).where(CycleForecast.user_id == user.id)
    )
    now = datetime.now(timezone.utc)
    for entry in entries:
        session.add(
            CycleForecast(
                user_id=user.id,
                cycle_start=entry.cycle_start,
                period_end=entry.period_end,
                ovulation=entry.ovulation,
                fertile_start=entry.fertile_start,
                fertile_end=entry.fertile_end,
                created_at=now,
            )
        )
    await session.flush()
    return len(entries)


async def latest_user_forecast(
    session: AsyncSession, user: User
) -> list[ForecastEntry]:
    """Return all stored forecast entries for *user* sorted by cycle_start.

    Used by the partner-view page to render the next predicted cycles.
    Returns an empty list when the user has never paired+pushed her
    forecast (rather than ``None``, which keeps the caller simple).
    """
    stmt = (
        select(CycleForecast)
        .where(CycleForecast.user_id == user.id)
        .order_by(asc(CycleForecast.cycle_start))
    )
    rows = (await session.execute(stmt)).scalars().all()
    today = date.today()
    out: list[ForecastEntry] = []
    upcoming_only: list[ForecastEntry] = []
    for r in rows:
        entry = ForecastEntry(
            cycle_start=r.cycle_start,
            period_end=r.period_end,
            ovulation=r.ovulation,
            fertile_start=r.fertile_start,
            fertile_end=r.fertile_end,
        )
        out.append(entry)
        if r.period_end >= today:
            upcoming_only.append(entry)
    # If we still have at least one cycle whose period_end is in the
    # future, return only those (the partner page should never show a
    # cycle that already finished weeks ago). Otherwise return the full
    # list so the page can show "месячные шли N дней назад" gracefully.
    return upcoming_only or out
