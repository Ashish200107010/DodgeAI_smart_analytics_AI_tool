from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.deps import DBConn, EdgeTypes
from app.api.schemas.graph import GraphPayload, Node, SubgraphRequest
from app.graph.service import GraphService


router = APIRouter(prefix="/api/graph", tags=["graph"])


@router.get("/nodes/{node_id}", response_model=Node)
def get_node(node_id: UUID, conn: DBConn) -> Node:
    return GraphService(conn).get_node(node_id)


@router.get("/nodes/{node_id}/neighbors", response_model=GraphPayload)
def get_neighbors(
    node_id: UUID,
    conn: DBConn,
    edge_types: EdgeTypes,
    direction: str = Query("both", pattern="^(in|out|both)$"),
    edgeTypeIds: list[UUID] | None = Query(default=None),
    includeGranular: bool = Query(default=True),
    limit: int = Query(default=200, ge=1, le=5000),
) -> GraphPayload:
    return GraphService(conn, edge_types=edge_types).get_neighbors(
        node_id=node_id,
        direction=direction,
        edge_type_ids=edgeTypeIds,
        include_granular=includeGranular,
        limit=limit,
    )


@router.post("/subgraph", response_model=GraphPayload)
def subgraph(req: SubgraphRequest, conn: DBConn, edge_types: EdgeTypes) -> GraphPayload:
    return GraphService(conn, edge_types=edge_types).get_subgraph(
        seed_node_ids=req.seedNodeIds,
        max_hops=req.maxHops,
        edge_type_ids=req.edgeTypeIds,
        include_granular=req.includeGranular,
        max_nodes=req.maxNodes,
        max_edges=req.maxEdges,
    )

