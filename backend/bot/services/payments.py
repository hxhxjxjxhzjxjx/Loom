"""Telegram Payments helpers + activation completion."""
from __future__ import annotations

import logging

from aiogram import Bot
from aiogram.types import LabeledPrice
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import get_settings
from bot.models import Order, OrderStatus, Tariff, User
from bot.services.codes import issue_code
from bot.services.subscriptions import create_subscription

log = logging.getLogger(__name__)

TARIFF_META: dict[Tariff, dict] = {
    Tariff.PREMIUM: {
        "title": "Lira Premium — 199₽/мес",
        "description": "Цифровой тариф: расширенная аналитика, прогноз "
        "овуляции, экспорт PDF/CSV, гайды. Без бокса.",
        "price": 199,
    },
    Tariff.BASIC: {
        "title": "Базовый бокс — 999₽/мес",
        "description": "До 5 предметов: гигиена, шоколад, уход. Каждый месяц.",
        "price": 999,
    },
    Tariff.VIP: {
        "title": "VIP бокс — 1999₽/мес",
        "description": "До 8 предметов + сюрприз: органика, шоколад ручной "
        "работы, 3 средства ухода, чай и гайды.",
        "price": 1999,
    },
}


async def send_invoice(bot: Bot, chat_id: int, tariff: Tariff) -> bool:
    """Send a Telegram Payments invoice. Returns False if PROVIDER_TOKEN is
    not configured (caller should fall back to manual flow)."""
    settings = get_settings()
    meta = TARIFF_META[tariff]
    if not settings.payment_provider_token:
        return False
    await bot.send_invoice(
        chat_id=chat_id,
        title=meta["title"],
        description=meta["description"],
        payload=f"flowcare:{tariff.value}",
        provider_token=settings.payment_provider_token,
        currency="RUB",
        prices=[LabeledPrice(label=meta["title"], amount=meta["price"] * 100)],
        start_parameter="subscription",
        need_email=False,
        need_shipping_address=False,
        is_flexible=False,
    )
    return True


async def finalize_payment(
    session: AsyncSession,
    *,
    user: User,
    tariff: Tariff,
    payment_id: str,
    amount_rub: int,
) -> tuple[Order, str]:
    """Persist Order, create Subscription, issue activation code.

    Returns (order, activation_code_value).
    """
    sub = await create_subscription(
        session, user=user, tariff=tariff, payment_id=payment_id
    )
    code = await issue_code(session, user=user, subscription=sub)
    order = Order(
        user_id=user.id,
        subscription_id=sub.id,
        status=OrderStatus.PAID,
        amount_rub=amount_rub,
        payment_provider="telegram",
        provider_payment_id=payment_id,
        paid_at=sub.started_at,
        snapshot={"tariff": tariff.value, "code": code.code},
    )
    session.add(order)
    await session.flush()
    return order, code.code
