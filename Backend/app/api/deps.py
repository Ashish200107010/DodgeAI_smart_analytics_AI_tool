from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.engine import Connection

from app.db.session import get_db
from app.domain.registry import EdgeTypeRegistry, edge_type_registry


DBConn = Annotated[Connection, Depends(get_db)]


def get_edge_type_registry() -> EdgeTypeRegistry:
    return edge_type_registry


EdgeTypes = Annotated[EdgeTypeRegistry, Depends(get_edge_type_registry)]

