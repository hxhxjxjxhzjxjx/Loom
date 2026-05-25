"""User-logged symptoms for the diary + trend charts.

Keyed by the device-local ``cycle_code`` so the diary works for everyone,
not only users who paired with the Telegram bot. When the user is paired
we also stamp ``user_id`` so future analytics can group by paired-user;
this column is optional.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import Date, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from bot.models.base import Base


class SymptomEntry(Base):
    __tablename__ = "symptom_entries"
    __table_args__ = (
        # Compound index for fast "give me last N days for this cycle_code".
        Index("ix_symptom_entries_cycle_day", "cycle_code", "day"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    # Device-local key — paired users send XXXX-XXXX cycle code, web /
    # unpaired clients send their device_id (``web-<random>-<ts>``,
    # ~20 chars). Treated as opaque, up to 64 chars.
    cycle_code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    # Optional FK — only set when the user has paired with Telegram.
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # ISO day of the entry; multiple symptoms per day → multiple rows.
    day: Mapped[date] = mapped_column(Date, nullable=False)
    # Free-text key (e.g. "cramps", "headache", "mood", "energy", "sleep").
    # Kept short and stable for grouping in trend graphs.
    symptom: Mapped[str] = mapped_column(String(48), nullable=False, index=True)
    # 1–5 intensity (0 = absent). Allows trend graphs.
    intensity: Mapped[int] = mapped_column(Integer, default=0)
    notes: Mapped[str | None] = mapped_column(String(512))
