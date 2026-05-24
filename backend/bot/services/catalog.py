"""Catalog seeder + small read helpers."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models import CatalogItem, CatalogTag

_SEED: list[dict] = [
    # Pads
    {"sku": "pads-always-ultra-normal", "name": "Always Ultra Normal", "brand": "Always",
     "category": CatalogTag.PADS, "price_rub": 220, "tags": ["mainstream"], "allergens": ["fragrance"]},
    {"sku": "pads-kotex-young-normal", "name": "Kotex Young Normal", "brand": "Kotex",
     "category": CatalogTag.PADS, "price_rub": 200, "tags": ["young"], "allergens": []},
    {"sku": "pads-naturella-camomile", "name": "Naturella Camomile", "brand": "Naturella",
     "category": CatalogTag.PADS, "price_rub": 210, "tags": ["sensitive_skin"], "allergens": []},
    {"sku": "pads-libresse-invisible", "name": "Libresse Invisible", "brand": "Libresse",
     "category": CatalogTag.PADS, "price_rub": 240, "tags": ["thin"], "allergens": []},
    {"sku": "pads-natracare-organic", "name": "Natracare Organic", "brand": "Natracare",
     "category": CatalogTag.PADS, "price_rub": 380, "tags": ["organic", "vegan", "sensitive_skin"], "allergens": []},
    # Tampons
    {"sku": "tampons-tampax-compak-normal", "name": "Tampax Compak Normal", "brand": "Tampax",
     "category": CatalogTag.TAMPONS, "price_rub": 320, "tags": [], "allergens": []},
    {"sku": "tampons-ob-procomfort-mini", "name": "o.b. ProComfort Mini", "brand": "o.b.",
     "category": CatalogTag.TAMPONS, "price_rub": 290, "tags": [], "allergens": []},
    {"sku": "tampons-kotex-click-super", "name": "Kotex Click Super", "brand": "Kotex",
     "category": CatalogTag.TAMPONS, "price_rub": 310, "tags": ["heavy"], "allergens": []},
    # Cup / panties
    {"sku": "cup-meluna", "name": "MeLuna Classic Cup", "brand": "MeLuna",
     "category": CatalogTag.CUP, "price_rub": 1990, "tags": ["eco"], "allergens": []},
    {"sku": "panties-thinx", "name": "Thinx Period Panties", "brand": "Thinx",
     "category": CatalogTag.PERIOD_PANTIES, "price_rub": 2490, "tags": ["eco"], "allergens": []},
    # Face care
    {"sku": "care-face-mask-aloe", "name": "Тканевая маска с алоэ", "brand": "Mixsoon",
     "category": CatalogTag.CARE_FACE, "price_rub": 250, "tags": ["sensitive_skin"], "allergens": []},
    {"sku": "care-face-cream-light", "name": "Лёгкий крем для лица", "brand": "CeraVe",
     "category": CatalogTag.CARE_FACE, "price_rub": 690, "tags": [], "allergens": []},
    # Body care
    {"sku": "care-body-handcream-rose", "name": "Крем для рук «Роза»", "brand": "Eveline",
     "category": CatalogTag.CARE_BODY, "price_rub": 220, "tags": ["fragrance:rose"], "allergens": ["fragrance"]},
    {"sku": "care-body-bath-oil-lavender", "name": "Масло для ванны «Лаванда»", "brand": "Weleda",
     "category": CatalogTag.CARE_BODY, "price_rub": 990, "tags": ["calming"], "allergens": ["essential_oils"]},
    {"sku": "care-body-scrub-vanilla", "name": "Сахарный скраб «Ваниль»", "brand": "Organic Shop",
     "category": CatalogTag.CARE_BODY, "price_rub": 350, "tags": ["sweet_scent"], "allergens": []},
    # Lips
    {"sku": "care-lips-balm-cherry", "name": "Бальзам для губ «Вишня»", "brand": "EOS",
     "category": CatalogTag.CARE_LIPS, "price_rub": 290, "tags": [], "allergens": []},
    {"sku": "care-lips-balm-vegan", "name": "Веганский бальзам для губ", "brand": "Lavera",
     "category": CatalogTag.CARE_LIPS, "price_rub": 340, "tags": ["vegan", "organic"], "allergens": []},
    # Sweets
    {"sku": "sweet-darkchoc-72", "name": "Тёмный шоколад 72%", "brand": "Lindt",
     "category": CatalogTag.SWEETS, "price_rub": 220, "tags": [], "allergens": ["chocolate", "lactose"]},
    {"sku": "sweet-handmade-truffles", "name": "Трюфели ручной работы", "brand": "Rossini",
     "category": CatalogTag.SWEETS, "price_rub": 690, "tags": ["handmade", "vip"], "allergens": ["chocolate", "nuts", "lactose"]},
    {"sku": "sweet-vegan-cookies", "name": "Веганское печенье", "brand": "Bite",
     "category": CatalogTag.SWEETS, "price_rub": 220, "tags": ["vegan", "gluten_free"], "allergens": []},
    {"sku": "sweet-fruit-jelly", "name": "Натуральный мармелад", "brand": "Bob Snail",
     "category": CatalogTag.SWEETS, "price_rub": 180, "tags": ["vegan", "gluten_free", "no_sugar"], "allergens": []},
    # Tea
    {"sku": "tea-chamomile", "name": "Чай ромашка", "brand": "Hipp",
     "category": CatalogTag.TEA, "price_rub": 180, "tags": ["calming"], "allergens": []},
    {"sku": "tea-mint-melissa", "name": "Чай мята-мелисса", "brand": "Curtis",
     "category": CatalogTag.TEA, "price_rub": 190, "tags": ["calming"], "allergens": []},
    {"sku": "tea-spiced-winter", "name": "Зимний пряный чай", "brand": "Tess",
     "category": CatalogTag.TEA, "price_rub": 240, "tags": [], "allergens": [], "seasons": ["winter", "autumn"]},
    # Gifts
    {"sku": "gift-soy-candle-vanilla", "name": "Соевая свеча «Ваниль»", "brand": "Aroma Home",
     "category": CatalogTag.GIFT, "price_rub": 590, "tags": ["calming", "sweet_scent"], "allergens": []},
    {"sku": "gift-cozy-socks", "name": "Тёплые носочки", "brand": "Falke",
     "category": CatalogTag.GIFT, "price_rub": 690, "tags": [], "allergens": [], "seasons": ["winter", "autumn"]},
    {"sku": "gift-sleep-mask-silk", "name": "Шёлковая маска для сна", "brand": "Slip",
     "category": CatalogTag.GIFT, "price_rub": 1290, "tags": ["vip"], "allergens": []},
    # Guides
    {"sku": "guide-cycle-care", "name": "Гайд: «Уход по фазам цикла»", "brand": "Flow",
     "category": CatalogTag.GUIDE, "price_rub": 0, "tags": ["digital", "vip"], "allergens": []},
    {"sku": "guide-pms-yoga", "name": "Гайд: «Йога при ПМС»", "brand": "Flow",
     "category": CatalogTag.GUIDE, "price_rub": 0, "tags": ["digital", "vip"], "allergens": []},
]


async def seed_catalog(session: AsyncSession) -> int:
    """Idempotent seeder. Inserts items missing by SKU. Returns number added."""
    added = 0
    for entry in _SEED:
        existing = await session.execute(
            select(CatalogItem).where(CatalogItem.sku == entry["sku"])
        )
        if existing.scalar_one_or_none() is not None:
            continue
        seasons = entry.get("seasons", [])
        item = CatalogItem(
            sku=entry["sku"],
            name=entry["name"],
            brand=entry.get("brand"),
            category=entry["category"],
            price_rub=entry.get("price_rub", 0),
            tags=entry.get("tags", []),
            allergens=entry.get("allergens", []),
            seasons=seasons,
        )
        session.add(item)
        added += 1
    return added


async def all_active(session: AsyncSession) -> list[CatalogItem]:
    stmt = select(CatalogItem).where(CatalogItem.active.is_(True))
    return list((await session.execute(stmt)).scalars())


async def by_category(
    session: AsyncSession, category: CatalogTag
) -> list[CatalogItem]:
    stmt = select(CatalogItem).where(
        CatalogItem.category == category, CatalogItem.active.is_(True)
    )
    return list((await session.execute(stmt)).scalars())
