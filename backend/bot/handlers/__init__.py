"""Routers exposed to bot.main."""
from aiogram import Router

from bot.handlers import (
    cabinet,
    onboarding,
    pairing,
    partner,
    payment,
    start,
    sync,
)

router = Router(name="root")
router.include_routers(
    pairing.router,
    partner.router,
    sync.router,
    start.router,
    onboarding.router,
    payment.router,
    cabinet.router,
)

__all__ = ["router"]
