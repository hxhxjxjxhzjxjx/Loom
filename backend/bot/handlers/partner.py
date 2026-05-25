"""``/start partner_<token>`` deep-link handler — partner mode.

When the cycle-owner taps "Поделиться с партнёром" in Lira, the app
generates a read-only token via ``POST /v1/lira/partner/invite`` and
hands her two URLs:

* ``/partner/<token>``                — read-only browser view, NO Telegram needed.
* ``t.me/<bot>?start=partner_<token>`` — Telegram deep-link the PARTNER taps so
                                         the bot remembers their chat id and can
                                         push proactive reminders to them.

The partner's first tap routes here. We claim the token against the
partner's Telegram user and reply with a short confirmation explaining
what they will receive (next-period reminder, day-of reminder).
"""
from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import CommandObject, CommandStart
from aiogram.types import Message

from bot.db import session_scope
from bot.services.partners import bind_partner_telegram, find_user_by_partner_token

log = logging.getLogger(__name__)
router = Router(name="partner")


@router.message(
    CommandStart(deep_link=True),
    F.text.regexp(r"^/start\s+partner_"),
)
async def on_start_with_partner(message: Message, command: CommandObject) -> None:
    raw = (command.args or "").strip()
    if not raw.lower().startswith("partner_"):
        return
    token = raw[len("partner_"):].strip()
    if not token or message.from_user is None:
        return

    partner_chat = message.from_user
    async with session_scope() as session:
        owner = await find_user_by_partner_token(session, token)
        if owner is None:
            await message.answer(
                "Ссылка партнёра устарела или недействительна. "
                "Попроси её сгенерировать новую — для этого в Lira нужно "
                "снова нажать «Поделиться с партнёром»."
            )
            return
        owner_name = (owner.first_name or owner.username or "она").strip()
        # Bind THIS Telegram user as the partner.
        await bind_partner_telegram(
            session,
            token=token,
            partner_telegram_id=partner_chat.id,
            partner_name=(
                partner_chat.full_name
                or partner_chat.first_name
                or partner_chat.username
            ),
        )

    await message.answer(
        "Готово! Теперь ты — партнёр в Lira 💫\n\n"
        f"Я буду присылать тебе короткие напоминания о цикле <b>{owner_name}</b>:\n"
        "• За <b>3 дня</b> до начала месячных — «скоро ПМС, побольше заботы».\n"
        "• В день начала — короткое напоминание.\n\n"
        "Ничего лишнего, никаких симптомов и личных деталей — только то, "
        "что помогает быть рядом.",
        parse_mode="HTML",
    )
