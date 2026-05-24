"""Box recommendation engine.

Filters the catalog by the user's profile (allergies, sensitivity,
diet, season, history novelty) and returns a list of CatalogItems
that fits the per-tariff item budget.
"""
from __future__ import annotations

import random
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models import CatalogItem, CatalogTag, DeliveryHistory, Profile, Tariff, User


# Per-tariff slot composition.
_BASIC_SLOTS: list[CatalogTag] = [
    CatalogTag.PADS,
    CatalogTag.PADS,
    CatalogTag.SWEETS,
    CatalogTag.CARE_FACE,
    CatalogTag.TEA,
]
_VIP_SLOTS: list[CatalogTag] = [
    CatalogTag.PADS,
    CatalogTag.TAMPONS,
    CatalogTag.CARE_FACE,
    CatalogTag.CARE_BODY,
    CatalogTag.CARE_LIPS,
    CatalogTag.SWEETS,
    CatalogTag.TEA,
    CatalogTag.GIFT,
]


def _season_for(d: date) -> str:
    m = d.month
    if m in (12, 1, 2):
        return "winter"
    if m in (3, 4, 5):
        return "spring"
    if m in (6, 7, 8):
        return "summer"
    return "autumn"


def _eligible(
    item: CatalogItem,
    *,
    allergies: set[str],
    sensitive_skin: bool,
    diet: str | None,
    season: str,
) -> bool:
    if not item.active:
        return False
    if any(a in allergies for a in item.allergens or []):
        return False
    if sensitive_skin and "fragrance" in (item.allergens or []):
        return False
    if diet == "vegan" and item.category == CatalogTag.SWEETS:
        if "vegan" not in (item.tags or []):
            return False
    if diet == "no_sugar" and item.category == CatalogTag.SWEETS:
        if "no_sugar" not in (item.tags or []):
            return False
    if item.seasons:
        if season not in item.seasons:
            return False
    return True


async def _previously_shipped_skus(
    session: AsyncSession, user: User, lookback: int = 3
) -> set[str]:
    stmt = (
        select(DeliveryHistory)
        .where(DeliveryHistory.user_id == user.id)
        .order_by(DeliveryHistory.created_at.desc())
        .limit(lookback)
    )
    history = (await session.execute(stmt)).scalars().all()
    seen: set[str] = set()
    for record in history:
        for entry in record.items or []:
            if "sku" in entry:
                seen.add(entry["sku"])
    return seen


async def build_box(
    session: AsyncSession,
    *,
    user: User,
    profile: Profile,
    tariff: Tariff,
    today: date | None = None,
) -> list[CatalogItem]:
    """Pick a list of catalog items for one shipment."""
    today = today or date.today()
    season = _season_for(today)
    slots = _BASIC_SLOTS if tariff == Tariff.BASIC else _VIP_SLOTS

    allergies = set(profile.allergies or [])
    diet = profile.diet
    sensitive = bool(profile.sensitive_skin)

    seen = await _previously_shipped_skus(session, user)
    novelty_score = profile.novelty_score or 3
    rng = random.Random(f"{user.id}-{today.isoformat()}")

    chosen: list[CatalogItem] = []
    chosen_skus: set[str] = set()

    for slot_category in slots:
        stmt = select(CatalogItem).where(
            CatalogItem.category == slot_category, CatalogItem.active.is_(True)
        )
        pool = list((await session.execute(stmt)).scalars())
        candidates = [
            it
            for it in pool
            if _eligible(
                it,
                allergies=allergies,
                sensitive_skin=sensitive,
                diet=diet,
                season=season,
            )
            and it.sku not in chosen_skus
        ]
        if not candidates:
            continue
        # Reward novelty: prefer items not recently shipped, weighted by
        # novelty_score (1..5).
        weights: list[float] = []
        for it in candidates:
            base = 1.0
            if it.sku not in seen:
                base += 0.4 * novelty_score
            if "vip" in (it.tags or []) and tariff == Tariff.VIP:
                base += 0.5
            weights.append(base)
        pick = rng.choices(candidates, weights=weights, k=1)[0]
        chosen.append(pick)
        chosen_skus.add(pick.sku)

    return chosen
