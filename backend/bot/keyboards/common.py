"""Inline keyboard builders for the questionnaire."""
from __future__ import annotations

from typing import Iterable

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton


def single_choice(
    options: Iterable[tuple[str, str]],
    *,
    columns: int = 1,
    skip: bool = False,
    back: bool = False,
) -> InlineKeyboardMarkup:
    """Build an inline keyboard for single-choice questions.

    `options` is an iterable of (callback_data, label). Adds a Skip / Back row
    when requested.
    """
    rows: list[list[InlineKeyboardButton]] = []
    buf: list[InlineKeyboardButton] = []
    for value, label in options:
        buf.append(InlineKeyboardButton(text=label, callback_data=value))
        if len(buf) == columns:
            rows.append(buf)
            buf = []
    if buf:
        rows.append(buf)

    nav: list[InlineKeyboardButton] = []
    if back:
        nav.append(InlineKeyboardButton(text="◀️ Назад", callback_data="nav:back"))
    if skip:
        nav.append(InlineKeyboardButton(text="Пропустить ⏭", callback_data="nav:skip"))
    if nav:
        rows.append(nav)

    return InlineKeyboardMarkup(inline_keyboard=rows)


def multi_choice(
    options: Iterable[tuple[str, str]],
    selected: set[str],
    *,
    columns: int = 1,
    skip: bool = False,
) -> InlineKeyboardMarkup:
    """Build a multi-select keyboard. Adds ✓ marks for already-selected values
    and a final «Готово» row."""
    rows: list[list[InlineKeyboardButton]] = []
    buf: list[InlineKeyboardButton] = []
    for value, label in options:
        prefix = "✅ " if value in selected else "▫️ "
        buf.append(
            InlineKeyboardButton(text=f"{prefix}{label}", callback_data=f"toggle:{value}")
        )
        if len(buf) == columns:
            rows.append(buf)
            buf = []
    if buf:
        rows.append(buf)

    nav: list[InlineKeyboardButton] = [
        InlineKeyboardButton(text="✅ Готово", callback_data="multi:done")
    ]
    if skip:
        nav.append(InlineKeyboardButton(text="Пропустить ⏭", callback_data="nav:skip"))
    rows.append(nav)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def yes_no(*, skip: bool = False) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(text="Да", callback_data="yes"),
            InlineKeyboardButton(text="Нет", callback_data="no"),
        ]
    ]
    if skip:
        rows.append([InlineKeyboardButton(text="Пропустить ⏭", callback_data="nav:skip")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm:yes")],
            [InlineKeyboardButton(text="↩️ Изменить", callback_data="confirm:edit")],
        ]
    )


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📦 Мой бокс"), KeyboardButton(text="✏️ Изменить профиль")],
            [KeyboardButton(text="⏸ Пауза"), KeyboardButton(text="ℹ️ Помощь")],
        ],
        resize_keyboard=True,
    )
