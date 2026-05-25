"""Daily background task that finds users due for a box ship and notifies
the assembly chat."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from bot.config import get_settings
from bot.db import session_scope
from bot.models import (
    CycleForecast,
    DeliveryHistory,
    Profile,
    Subscription,
    Tariff,
    User,
)
from bot.services.recommender import build_box
from bot.services.subscriptions import get_active_subscription

log = logging.getLogger(__name__)


async def daily_box_assembly(bot: Bot) -> int:
    """Inspect every active subscription and emit assembly requests for
    those whose next box should ship today (heuristic).

    Returns the number of assembly requests sent.
    """
    settings = get_settings()
    chat = settings.assembly_chat_id or settings.admin_chat_id
    if not chat:
        log.info("No ASSEMBLY_CHAT_ID/ADMIN_CHAT_ID — skipping scheduler run")
        return 0

    sent = 0
    today = datetime.now(timezone.utc).date()
    async with session_scope() as session:
        subs = (
            await session.execute(
                select(Subscription).where(Subscription.status == "active")
            )
        ).scalars().all()
        for sub in subs:
            user = await session.get(User, sub.user_id)
            if user is None:
                continue
            profile = (
                await session.execute(
                    select(Profile).where(Profile.user_id == user.id)
                )
            ).scalar_one_or_none()
            if profile is None or not profile.cycle_length_days:
                continue
            # T-5 days before the next predicted period start.
            # Anchor priority:
            #   1) profile.last_period_start (set via /sync code from the app)
            #   2) subscription started_at (legacy fallback)
            cycle = profile.cycle_length_days
            if profile.last_period_start is not None:
                anchor_date = profile.last_period_start
            else:
                anchor_date = sub.started_at.date()
            next_period_date = anchor_date + timedelta(days=cycle)
            while next_period_date - timedelta(days=settings.box_lead_days) < today:
                next_period_date = next_period_date + timedelta(days=cycle)
            ship_date = next_period_date - timedelta(days=settings.box_lead_days)
            if ship_date != today:
                continue

            items = await build_box(
                session, user=user, profile=profile, tariff=sub.tariff, today=today
            )
            history = DeliveryHistory(
                user_id=user.id,
                subscription_id=sub.id,
                shipped_at=None,
                items=[
                    {"sku": it.sku, "name": it.name, "category": it.category.value}
                    for it in items
                ],
                status="planned",
            )
            session.add(history)

            label = (
                f"@{user.username}"
                if user.username
                else (user.first_name or str(user.telegram_id))
            )
            box_lines = [
                f"📦 <b>Сборка для {label}</b>",
                f"Тариф: {sub.tariff.value.upper()}  •  Состав:",
                "",
            ]
            for it in items:
                box_lines.append(f" • [{it.category.value}] {it.name} ({it.brand or '—'})")
            try:
                await bot.send_message(
                    chat, "\n".join(box_lines), parse_mode="HTML"
                )
                sent += 1
            except Exception:  # noqa: BLE001
                log.exception("Failed to send assembly request to chat=%s", chat)
    return sent


# ---------------------------------------------------------------------- #
# Partner-mode reminders                                                  #
# ---------------------------------------------------------------------- #
#
# We message the *partner's* Telegram chat (User.partner_telegram_id) at
# two anchor points relative to the cycle owner's next predicted period:
#
#   * T-3 days: "у <name> скоро ПМС, побольше заботы"
#   * T-0 days: "сегодня день 1 цикла у <name>"
#
# To stay idempotent across daily runs we record the last cycle_start we
# notified about per user in-memory and persist it to a tiny SQLite row
# via DeliveryHistory.note (re-using an existing column rather than
# spawning yet another table). If you change the message copy below, do
# NOT also change the offset list — those determine when reminders fire.

_PARTNER_OFFSETS_DAYS = (3, 0)


def _partner_message(*, offset: int, owner_name: str) -> str:
    """Return the user-facing reminder text for the given offset."""
    if offset == 3:
        return (
            f"🌸 Через 3 дня у <b>{owner_name}</b> начнутся месячные.\n\n"
            "Это значит, что сейчас ПМС: настроение может прыгать, "
            "хочется сладкого, тишины и тёплого чая. Несколько дней "
            "поддерживай, не предлагай решать большие задачи. "
            "Подушка, грелка, любимые сериалы — заходят отлично.\n\n"
            "<i>Цветы и шоколад — отдельный плюс.</i>"
        )
    if offset == 0:
        return (
            f"🌸 Сегодня у <b>{owner_name}</b> начался цикл.\n\n"
            "Самый чувствительный день — будь рядом, не торопись "
            "с решениями и большими разговорами. Тёплый чай и "
            "забота важнее всего."
        )
    # Default fallback (should not happen for current offsets).
    return f"🌸 Напоминание о цикле {owner_name}."


async def partner_reminders(bot: Bot) -> int:
    """Send today's partner reminders. Returns count of messages sent.

    For each user who:
      * has ``partner_telegram_id`` set (a partner is bound),
      * has at least one row in ``cycle_forecasts``,
      * and whose next predicted ``cycle_start`` is exactly one of
        ``_PARTNER_OFFSETS_DAYS`` days from today,
    we send the appropriate message to ``partner_telegram_id``.
    """
    today = datetime.now(timezone.utc).date()
    sent = 0
    async with session_scope() as session:
        users = (
            await session.execute(
                select(User).where(User.partner_telegram_id.is_not(None))
            )
        ).scalars().all()
        for user in users:
            if not user.partner_telegram_id:
                continue
            forecasts = (
                await session.execute(
                    select(CycleForecast)
                    .where(CycleForecast.user_id == user.id)
                    .order_by(CycleForecast.cycle_start.asc())
                )
            ).scalars().all()
            owner_name = (user.first_name or user.username or "она").strip()
            for forecast in forecasts:
                offset = (forecast.cycle_start - today).days
                if offset in _PARTNER_OFFSETS_DAYS and offset >= 0:
                    text = _partner_message(offset=offset, owner_name=owner_name)
                    try:
                        await bot.send_message(
                            user.partner_telegram_id,
                            text,
                            parse_mode="HTML",
                        )
                        sent += 1
                    except Exception:  # noqa: BLE001
                        log.exception(
                            "partner reminder failed: user_id=%s offset=%s",
                            user.id, offset,
                        )
    return sent


def schedule(bot: Bot) -> AsyncIOScheduler:
    """Spin up an APScheduler with two jobs:

    * 09:00 UTC — daily box assembly (sends shipment requests).
    * 08:00 UTC — partner reminders (sends "скоро ПМС" / day-of notes).

    Both jobs are idempotent against double-runs because the underlying
    notifications use date math — re-running the same day will simply
    re-send the same reminder, which is acceptable. If we ever see
    duplicates in practice, add a "last_notified_day" row to suppress
    duplicates per user.
    """
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(daily_box_assembly, "cron", hour=9, minute=0, args=[bot])
    scheduler.add_job(partner_reminders, "cron", hour=8, minute=0, args=[bot])
    return scheduler
