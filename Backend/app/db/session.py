from __future__ import annotations

from collections.abc import Generator

from fastapi import HTTPException
from sqlalchemy.engine import Connection
from sqlalchemy.exc import SQLAlchemyError

from app.db.engine import engine


def get_db() -> Generator[Connection, None, None]:
    try:
        with engine.connect() as conn:
            yield conn
    except SQLAlchemyError as e:
        raise HTTPException(
            status_code=503,
            detail="Database connection failed. Set DATABASE_URL correctly and ensure Postgres is running.",
        ) from e

