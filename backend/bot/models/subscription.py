from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.models.base import Base

if TYPE_CHECKING:
    from bot.models.user import User
    from bot.models.activation_code import ActivationCode


class Tariff(enum.Enum):
    PREMIUM = "premium"
    BASIC = "basic"
    VIP = "vip"


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    tariff: Mapped[Tariff] = mapped_column(SAEnum(Tariff, name="tariff"), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="active")
    payment_id: Mapped[str | None] = mapped_column(String(128))

    user: Mapped["User"] = relationship("User", back_populates="subscriptions")
    activation_code: Mapped["ActivationCode | None"] = relationship(
        "ActivationCode", back_populates="subscription", uselist=False
    )
