from __future__ import annotations

import enum

from sqlalchemy import Enum as SAEnum, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from bot.models.base import Base


class CatalogTag(enum.Enum):
    PADS = "pads"
    TAMPONS = "tampons"
    CUP = "cup"
    PERIOD_PANTIES = "period_panties"
    CARE_FACE = "care_face"
    CARE_BODY = "care_body"
    CARE_LIPS = "care_lips"
    SWEETS = "sweets"
    TEA = "tea"
    GIFT = "gift"
    GUIDE = "guide"


class CatalogItem(Base):
    __tablename__ = "catalog_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    sku: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(256))
    brand: Mapped[str | None] = mapped_column(String(128))
    category: Mapped[CatalogTag] = mapped_column(
        SAEnum(CatalogTag, name="catalog_tag"), nullable=False, index=True
    )
    description: Mapped[str | None] = mapped_column(Text)
    price_rub: Mapped[int] = mapped_column(Integer, default=0)
    tags: Mapped[list[str]] = mapped_column(
        JSON,
        default=list,
        doc="Free-form tags: vegan, gluten_free, organic, season:winter, "
        "phase:luteal, sensitive_skin, ...",
    )
    allergens: Mapped[list[str]] = mapped_column(JSON, default=list)
    seasons: Mapped[list[str]] = mapped_column(JSON, default=list)
    active: Mapped[bool] = mapped_column(default=True)
