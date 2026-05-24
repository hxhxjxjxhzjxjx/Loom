from __future__ import annotations

from typing import TYPE_CHECKING, Any

from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.models.base import Base

if TYPE_CHECKING:
    from bot.models.user import User


class Profile(Base):
    """Per-user questionnaire answers + delivery address."""

    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)

    # Step 1: basic
    name: Mapped[str | None] = mapped_column(String(128))
    birth_year: Mapped[int | None] = mapped_column(Integer)
    city: Mapped[str | None] = mapped_column(String(128))
    cycle_length_days: Mapped[int | None] = mapped_column(Integer)
    period_length_days: Mapped[int | None] = mapped_column(Integer)
    flow_app_code: Mapped[str | None] = mapped_column(String(32))

    # Cycle sync (set via /sync code from the app)
    last_period_start: Mapped[date | None] = mapped_column(Date)
    cycle_sync_code: Mapped[str | None] = mapped_column(String(16))

    # Step 2: hygiene preferences (multi-select catalog item IDs and choices)
    hygiene_pads: Mapped[list[str]] = mapped_column(JSON, default=list)
    hygiene_tampons: Mapped[list[str]] = mapped_column(JSON, default=list)
    hygiene_other: Mapped[list[str]] = mapped_column(JSON, default=list)
    flow_heaviness: Mapped[str | None] = mapped_column(String(32))

    # Step 3: allergies & sensitivity
    allergies: Mapped[list[str]] = mapped_column(JSON, default=list)
    sensitive_skin: Mapped[bool | None] = mapped_column()
    allergy_notes: Mapped[str | None] = mapped_column(Text)

    # Step 4: lifestyle
    diet: Mapped[str | None] = mapped_column(String(32))
    goal: Mapped[str | None] = mapped_column(String(32))
    joys: Mapped[list[str]] = mapped_column(JSON, default=list)
    novelty_score: Mapped[int | None] = mapped_column(Integer)
    dislikes: Mapped[str | None] = mapped_column(Text)

    # Step 5: deep preferences
    favorite_season: Mapped[str | None] = mapped_column(String(16))
    calming: Mapped[list[str]] = mapped_column(JSON, default=list)
    occupation: Mapped[str | None] = mapped_column(String(64))
    hobbies: Mapped[str | None] = mapped_column(Text)

    # Step 6: address
    address_country: Mapped[str | None] = mapped_column(String(64))
    address_city: Mapped[str | None] = mapped_column(String(128))
    address_street: Mapped[str | None] = mapped_column(String(128))
    address_building: Mapped[str | None] = mapped_column(String(32))
    address_apartment: Mapped[str | None] = mapped_column(String(32))
    address_postal: Mapped[str | None] = mapped_column(String(16))
    address_phone: Mapped[str | None] = mapped_column(String(32))

    # Free-form: allows future fields without migration
    extra: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    user: Mapped["User"] = relationship("User", back_populates="profile")
