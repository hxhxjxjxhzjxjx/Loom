"""Repository helpers for User + Profile."""
from __future__ import annotations

from aiogram.types import User as TGUser
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models import Profile, User


async def get_or_create_user(session: AsyncSession, tg_user: TGUser) -> User:
    """Look up by telegram_id and create row if missing.

    Race-safe: when several /start updates arrive at once Telegram may dispatch
    them concurrently; if two transactions both miss the SELECT they will both
    try to INSERT and one will hit the UNIQUE(telegram_id) constraint. We
    recover by rolling back the failed insert and re-fetching the row that the
    other transaction wrote.
    """
    stmt = select(User).where(User.telegram_id == tg_user.id)
    user = (await session.execute(stmt)).scalar_one_or_none()
    if user is None:
        user = User(
            telegram_id=tg_user.id,
            username=tg_user.username,
            first_name=tg_user.first_name,
            language_code=tg_user.language_code,
        )
        session.add(user)
        try:
            await session.flush()
        except IntegrityError:
            await session.rollback()
            user = (await session.execute(stmt)).scalar_one()
    if user is not None:
        user.username = tg_user.username
        user.first_name = tg_user.first_name
        user.language_code = tg_user.language_code
    return user


async def get_or_create_profile(session: AsyncSession, user: User) -> Profile:
    stmt = select(Profile).where(Profile.user_id == user.id)
    profile = (await session.execute(stmt)).scalar_one_or_none()
    if profile is None:
        profile = Profile(user_id=user.id)
        session.add(profile)
        try:
            await session.flush()
        except IntegrityError:
            await session.rollback()
            profile = (await session.execute(stmt)).scalar_one()
    return profile
