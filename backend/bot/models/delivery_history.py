from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from bot.models.base import Base


class DeliveryHistory(Base):
    """Record of a single shipped box, used for novelty + algorithm input."""

    __tablename__ = "delivery_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    subscription_id: Mapped[int | None] = mapped_column(
        ForeignKey("subscriptions.id", ondelete="SET NULL")
    )
    shipped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    items: Mapped[list[dict]] = mapped_column(
        JSON, default=list, doc="Snapshot of {sku, name, category} of items in this box."
    )
    status: Mapped[str] = mapped_column(String(32), default="planned")
