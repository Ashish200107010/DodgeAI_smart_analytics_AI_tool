from __future__ import annotations

import uuid as uuidlib

from fastapi import APIRouter
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.deps import DBConn, EdgeTypes
from app.api.schemas.domain import EdgeType
from app.domain.edge_types import EDGE_TYPE_NAMESPACE


router = APIRouter(prefix="/api/domain", tags=["domain"])


@router.get("/edge-types", response_model=list[EdgeType])
def list_edge_types(conn: DBConn, edge_types: EdgeTypes) -> list[EdgeType]:
    """
    Return relationship types for the Mapping dropdown.

    Expected behavior for the demo:
    - list edge types that actually exist in `graph.graph_edges`
    - enrich with metadata from the registry when available
    """
    try:
        # Keep this endpoint fast; if DB is cold/slow we prefer a quick fallback
        # to avoid upstream (Render/Neon) request timeouts on first load.
        with conn.begin():
            conn.execute(text("SET LOCAL statement_timeout = '2000ms'"))
            rows = conn.execute(text("SELECT DISTINCT edge_type FROM graph.graph_edges ORDER BY edge_type")).all()
        codes = [r[0] for r in rows if r and r[0]]
    except SQLAlchemyError:
        # Fallback: registry definitions only (useful before the graph projection exists)
        codes = [et.code for et in edge_types.all()]

    out: list[EdgeType] = []
    seen: set[str] = set()
    for code in codes:
        if not code or code in seen:
            continue
        seen.add(code)

        et = edge_types.get_by_code(code)
        if et is not None:
            out.append(
                EdgeType(
                    id=et.id,
                    code=et.code,
                    displayName=f"{et.code} — {et.display_name}",
                    description=et.description,
                    srcNodeType=et.src_node_type,
                    dstNodeType=et.dst_node_type,
                    isGranular=et.is_granular,
                    group=et.group,
                )
            )
        else:
            out.append(
                EdgeType(
                    id=uuidlib.uuid5(EDGE_TYPE_NAMESPACE, code),
                    code=code,
                    displayName=code,
                    description=f"Relationship type {code}",
                    srcNodeType=None,
                    dstNodeType=None,
                    isGranular=False,
                    group="other",
                )
            )

    return out

