"""Lightweight, idempotent column upgrades that augment Base.metadata.create_all.

``create_all`` only creates missing tables — it never alters existing ones.
When we add a column to an existing model (e.g. ``User.partner_token``),
old SQLite databases that were created before the column existed will
break with ``OperationalError: no such column``.

To stay simple (no Alembic) we run a tiny per-column ``ALTER TABLE … ADD
COLUMN`` at startup. The retrofit is idempotent: we read ``PRAGMA
table_info`` first and only ALTER columns that are missing.

Add new columns by appending to ``_RETROFIT_COLUMNS``; never remove or
rename existing entries (removing would not drop the column but it would
silently stop us upgrading new clones).
"""
from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

log = logging.getLogger("schema-upgrade")


# Each tuple: (table, column, sqlite_type_ddl).
_RETROFIT_COLUMNS: tuple[tuple[str, str, str], ...] = (
    ("users", "partner_token",        "VARCHAR(32)"),
    ("users", "partner_telegram_id",  "BIGINT"),
    ("users", "partner_name",         "VARCHAR(128)"),
)


async def _existing_columns(conn: AsyncConnection, table: str) -> set[str]:
    rows = await conn.execute(text(f"PRAGMA table_info({table})"))
    # SQLite's PRAGMA returns rows of (cid, name, type, notnull, dflt, pk)
    return {row[1] for row in rows.fetchall()}


async def retrofit_columns(conn: AsyncConnection) -> None:
    """Apply each ALTER TABLE … ADD COLUMN if it is missing."""
    cache: dict[str, set[str]] = {}
    for table, column, ddl in _RETROFIT_COLUMNS:
        cols = cache.get(table)
        if cols is None:
            cols = await _existing_columns(conn, table)
            cache[table] = cols
        if column in cols:
            continue
        try:
            await conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}"))
            cols.add(column)
            log.info("schema-upgrade: added %s.%s", table, column)
        except Exception as exc:  # pragma: no cover — defensive
            log.warning("schema-upgrade: failed %s.%s — %s", table, column, exc)


async def _index_exists(conn: AsyncConnection, index: str) -> bool:
    rows = await conn.execute(
        text("SELECT 1 FROM sqlite_master WHERE type='index' AND name=:n").bindparams(n=index)
    )
    return rows.first() is not None


async def ensure_indexes(conn: AsyncConnection) -> None:
    """Create indexes on retrofitted columns (idempotent)."""
    targets = (
        ("ix_users_partner_token",        "users", "partner_token"),
        ("ix_users_partner_telegram_id",  "users", "partner_telegram_id"),
    )
    for name, table, column in targets:
        if await _index_exists(conn, name):
            continue
        try:
            await conn.execute(text(f"CREATE INDEX {name} ON {table}({column})"))
            log.info("schema-upgrade: created %s", name)
        except Exception as exc:  # pragma: no cover
            log.warning("schema-upgrade: index %s — %s", name, exc)
