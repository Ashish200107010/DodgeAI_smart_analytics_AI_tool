from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.engine import Connection

from app.db.run_sql import fetch_all, fetch_one


class GraphRepository:
    def __init__(self, conn: Connection) -> None:
        self._conn = conn

    def get_node(self, node_id: UUID) -> dict[str, Any] | None:
        return fetch_one(
            self._conn,
            ("graph", "get_node.sql"),
            {"node_id": node_id},
        )

    def get_degrees(self, node_id: UUID) -> dict[str, Any]:
        row = fetch_one(
            self._conn,
            ("graph", "get_degrees.sql"),
            {"node_id": node_id},
        )
        return row or {"in_degree": 0, "out_degree": 0}

    def get_nodes_by_ids(self, node_ids: list[UUID]) -> list[dict[str, Any]]:
        if not node_ids:
            return []
        return fetch_all(
            self._conn,
            ("graph", "get_nodes_by_ids.sql"),
            {"node_ids": node_ids},
        )

    def get_node_id_by_key(self, node_key: str) -> UUID | None:
        row = fetch_one(
            self._conn,
            ("graph", "get_node_id_by_key.sql"),
            {"node_key": node_key},
        )
        if not row:
            return None
        return row["node_id"]

    def get_edges_for_node(
        self,
        *,
        node_id: UUID,
        direction: str,
        edge_type_codes: list[str],
        limit: int,
    ) -> list[dict[str, Any]]:
        return fetch_all(
            self._conn,
            ("graph", "neighbors.sql"),
            {
                "node_id": node_id,
                "direction": direction,
                "edge_type_codes": edge_type_codes,
                "limit": limit,
            },
        )

    def get_subgraph_edges(
        self,
        *,
        seed_node_ids: list[UUID],
        max_hops: int,
        edge_type_codes: list[str],
        max_edges: int,
    ) -> list[dict[str, Any]]:
        if not seed_node_ids or not edge_type_codes:
            return []
        return fetch_all(
            self._conn,
            ("graph", "subgraph_edges.sql"),
            {
                "seed_node_ids": seed_node_ids,
                "max_hops": max_hops,
                "edge_type_codes": edge_type_codes,
                "max_edges": max_edges,
            },
        )

