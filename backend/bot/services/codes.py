"""Activation code generation + redemption."""
from __future__ import annotations

import secrets
import string
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models import ActivationCode, Subscription, User

_ALPHABET = string.ascii_uppercase + string.digits  # excluded confusing 0/O later
_AMBIG = {"0", "O", "I", "1"}
_SAFE_ALPHABET = "".join(c for c in _ALPHABET if c not in _AMBIG)


def _new_code(length: int = 8) -> str:
    return "".join(secrets.choice(_SAFE_ALPHABET) for _ in range(length))


async def issue_code(
    session: AsyncSession, *, user: User, subscription: Subscription
) -> ActivationCode:
    """Generate a unique 8-character code and persist it."""
    for _ in range(10):
        code_value = _new_code()
        existing = await session.execute(
            select(ActivationCode).where(ActivationCode.code == code_value)
        )
        if existing.scalar_one_or_none() is None:
            break
    else:  # pragma: no cover — astronomically unlikely
        raise RuntimeError("Failed to generate unique activation code")

    code = ActivationCode(
        code=code_value, user_id=user.id, subscription_id=subscription.id
    )
    session.add(code)
    await session.flush()
    return code


async def find_code(session: AsyncSession, code: str) -> ActivationCode | None:
    stmt = select(ActivationCode).where(ActivationCode.code == code.upper())
    return (await session.execute(stmt)).scalar_one_or_none()


async def redeem_code(
    session: AsyncSession, code_value: str, *, device_id: str | None = None
) -> tuple[ActivationCode, Subscription] | None:
    """Mark a code as redeemed and return (code, subscription) on success.

    Returns None if the code is unknown, already redeemed by a different
    device, or its subscription has expired.
    """
    code = await find_code(session, code_value)
    if code is None:
        return None
    sub = await session.get(Subscription, code.subscription_id)
    if sub is None:
        return None
    expires = sub.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires < datetime.now(timezone.utc):
        return None
    if code.redeemed_at is None:
        code.redeemed_at = datetime.now(timezone.utc)
        code.redeemed_by_device = device_id
    return code, sub
