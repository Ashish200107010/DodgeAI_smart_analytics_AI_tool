from __future__ import annotations

from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection


SQL_DIR = Path(__file__).resolve().parent / "sql"


def load_sql(*parts: str) -> str:
    path = SQL_DIR.joinpath(*parts)
    return path.read_text(encoding="utf-8")


def fetch_all(
    conn: Connection,
    sql_parts: tuple[str, ...],
    params: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    sql = load_sql(*sql_parts)
    result = conn.execute(text(sql), params or {})
    return [dict(row) for row in result.mappings().all()]


def fetch_one(
    conn: Connection,
    sql_parts: tuple[str, ...],
    params: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    rows = fetch_all(conn, sql_parts, params)
    return rows[0] if rows else None

