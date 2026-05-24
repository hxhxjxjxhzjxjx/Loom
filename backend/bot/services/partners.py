"""Partner-mode helpers: read-only share token + linking to a Telegram chat.

The flow is symmetric to ``services.pairing`` but ends with a different
state: instead of identifying which user owns a fresh device, we record
WHO the partner is (their Telegram chat id) so the bot can send them
proactive notifications ("у <name> скоро ПМС, купи цветы").
"""
from __future__ import annotations

import secrets

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models import User


def _new_token(nbytes: int = 16) -> str:
    """URL-safe random token (32 chars after base64-urlsafe encoding)."""
    return secrets.token_urlsafe(nbytes)[:32]


async def ensure_partner_token(session: AsyncSession, user: User) -> str:
    """Generate ``user.partner_token`` if it is not set, return it.

    Idempotent — calling twice gives back the same token. The token is a
    bearer-style secret: any Telegram user who follows the deep-link with
    it will be bound as this user's partner.
    """
    if user.partner_token:
        return user.partner_token
    user.partner_token = _new_token()
    await session.flush()
    return user.partner_token


async def find_user_by_partner_token(
    session: AsyncSession, token: str
) -> User | None:
    if not token:
        return None
    stmt = select(User).where(User.partner_token == token)
    return (await session.execute(stmt)).scalar_one_or_none()


async def bind_partner_telegram(
    session: AsyncSession,
    *,
    token: str,
    partner_telegram_id: int,
    partner_name: str | None,
) -> User | None:
    """Mark the User identified by ``token`` as having a paired partner.

    Returns the User on success, ``None`` if the token is unknown.
    The token stays valid after binding — the partner can re-open the
    deep-link later without breaking things — but calling this function
    overwrites the previous partner (only one partner per user).
    """
    user = await find_user_by_partner_token(session, token)
    if user is None:
        return None
    user.partner_telegram_id = partner_telegram_id
    user.partner_name = (partner_name or "").strip()[:128] or None
    await session.flush()
    return user


def partner_share_url(base_url: str, token: str) -> str:
    """Build the read-only share URL — open in a browser, NOT Telegram."""
    base = (base_url or "").rstrip("/")
    return f"{base}/partner/{token}"


def partner_bot_deeplink(bot_username: str, token: str) -> str:
    """Build the Telegram deep-link the partner taps to bind their chat."""
    username = (bot_username or "").lstrip("@") or "lowerBsk24_bot"
    return f"https://t.me/{username}?start=partner_{token}"
