"""Personal cabinet: /mybox, edit profile, pause/cancel."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from sqlalchemy import desc, select

from bot.config import get_settings
from bot.db import session_scope
from bot.models import DeliveryHistory, Profile
from bot.services.subscriptions import get_active_subscription
from bot.services.users import get_or_create_user

log = logging.getLogger(__name__)
router = Router(name="cabinet")


@router.message(Command("mybox"))
async def my_box_cmd(message: Message) -> None:
    await _render_status(message)


@router.message(F.text == "📦 Мой бокс")
async def my_box_btn(message: Message) -> None:
    await _render_status(message)


@router.callback_query(F.data == "cabinet:status")
async def my_box_cb(cb: CallbackQuery) -> None:
    await _render_status(cb.message, cb_user=cb.from_user)
    await cb.answer()


async def _render_status(message: Message, cb_user=None) -> None:
    user_tg = cb_user or message.from_user
    settings = get_settings()
    async with session_scope() as session:
        user = await get_or_create_user(session, user_tg)
        sub = await get_active_subscription(session, user)
        profile = (
            await session.execute(select(Profile).where(Profile.user_id == user.id))
        ).scalar_one_or_none()

        last_delivery = (
            await session.execute(
                select(DeliveryHistory)
                .where(DeliveryHistory.user_id == user.id)
                .order_by(desc(DeliveryHistory.created_at))
                .limit(1)
            )
        ).scalar_one_or_none()

    if sub is None:
        await message.answer(
            "У тебя пока нет активной подписки. Чтобы оформить — /setup",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="✨ Оформить подписку",
                            callback_data="onboarding:start",
                        )
                    ]
                ]
            ),
        )
        return

    next_box = _predict_next_box_date(profile, settings.box_lead_days)
    expires = sub.expires_at
    text = [
        "📦 <b>Твой бокс</b>",
        "",
        f"Тариф: <b>{sub.tariff.value.upper()}</b>",
        f"Подписка активна до: <b>{expires.strftime('%d.%m.%Y')}</b>",
    ]
    if next_box:
        text.append(f"Ближайшая отправка: <b>{next_box.strftime('%d.%m.%Y')}</b>")
    if last_delivery and last_delivery.items:
        items_lines = [
            f"  • {it.get('name', it.get('sku', '?'))}"
            for it in last_delivery.items
        ]
        text.append("")
        text.append("Прошлый бокс:")
        text.extend(items_lines)

    await message.answer(
        "\n".join(text),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✏️ Изменить профиль", callback_data="cabinet:edit"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="⏸ Поставить на паузу", callback_data="cabinet:pause"
                    )
                ],
            ]
        ),
    )


def _predict_next_box_date(
    profile: Profile | None, lead_days: int
) -> datetime | None:
    if profile is None or not profile.cycle_length_days:
        return None
    # Without an actual last-period date stored on the bot side, we
    # estimate a window: assume next period in `cycle_length_days` and
    # ship `lead_days` before. UI in the app fills the real LMP.
    today = datetime.now(timezone.utc)
    next_period = today + timedelta(days=profile.cycle_length_days // 2)
    return next_period - timedelta(days=lead_days)


@router.callback_query(F.data == "cabinet:pause")
async def pause(cb: CallbackQuery) -> None:
    settings = get_settings()
    if settings.admin_chat_id:
        try:
            await cb.bot.send_message(
                settings.admin_chat_id,
                f"⏸ Пользователь @{cb.from_user.username or cb.from_user.id} "
                f"просит поставить подписку на паузу.",
            )
        except Exception:  # noqa: BLE001
            log.exception("Failed to notify admin")
    await cb.message.answer(
        "Окей, передала менеджеру. Свяжемся в ближайшее время. "
        "Если хочешь, напиши прямо в этот чат."
    )
    await cb.answer()


@router.callback_query(F.data == "cabinet:edit")
async def edit_profile(cb: CallbackQuery) -> None:
    await cb.message.answer(
        "Чтобы перепройти опросник — /setup. Все ответы перезапишутся."
    )
    await cb.answer()
