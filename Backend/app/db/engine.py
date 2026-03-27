from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from app.core.config import settings


engine: Engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    # Fail fast on cold/slow DB handshakes so proxies don't return 504.
    connect_args={"connect_timeout": 10},
)

