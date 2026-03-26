from __future__ import annotations

from typing import Any

from sqlalchemy.engine import Connection

from app.db.run_sql import fetch_all


class ChatRepository:
    def __init__(self, conn: Connection) -> None:
        self._conn = conn

    def run_template(self, template: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        # Templates live under app/db/sql/chat/templates/<template>.sql
        return fetch_all(self._conn, ("chat", "templates", f"{template}.sql"), params)

