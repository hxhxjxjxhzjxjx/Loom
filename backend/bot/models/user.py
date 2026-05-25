from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.models.base import Base

if TYPE_CHECKING:
    from bot.models.profile import Profile
    from bot.models.subscription import Subscription
    from bot.models.activation_code import ActivationCode


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(64))
    first_name: Mapped[str | None] = mapped_column(String(128))
    language_code: Mapped[str | None] = mapped_column(String(8))

    # --- Partner mode ----------------------------------------------------- #
    # Random read-only token. Anyone with /partner/<token> URL sees the
    # cycle in a read-only view (next period date, current phase). Used
    # to share the cycle with a partner (e.g. husband, girlfriend) via
    # Telegram bot deep-link. NULL by default — user must opt in.
    partner_token: Mapped[str | None] = mapped_column(
        String(32), unique=True, index=True
    )
    # Telegram user_id of the partner who claimed the token via the
    # bot's /start partner_<token> handler. Lets us send proactive
    # notifications ("у Иры скоро ПМС") to the partner's Telegram.
    partner_telegram_id: Mapped[int | None] = mapped_column(
        BigInteger, unique=False, index=True, nullable=True
    )
    partner_name: Mapped[str | None] = mapped_column(String(128))

    profile: Mapped["Profile | None"] = relationship(
        "Profile", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    subscriptions: Mapped[list["Subscription"]] = relationship(
        "Subscription", back_populates="user", cascade="all, delete-orphan"
    )
    activation_codes: Mapped[list["ActivationCode"]] = relationship(
        "ActivationCode", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<User id={self.id} tg={self.telegram_id} @{self.username}>"
