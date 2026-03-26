from __future__ import annotations

from typing import Any
from uuid import UUID

import uuid as uuidlib
from sqlalchemy.engine import Connection
from sqlalchemy.exc import SQLAlchemyError
from fastapi import HTTPException

from app.api.schemas.graph import Degrees, Edge, GraphPayload, Node
from app.domain.edge_types import EDGE_TYPE_NAMESPACE
from app.domain.registry import EdgeTypeRegistry, edge_type_registry
from app.graph.repository import GraphRepository


class GraphService:
    def __init__(self, conn: Connection, *, edge_types: EdgeTypeRegistry | None = None) -> None:
        self._repo = GraphRepository(conn)
        self._edge_types = edge_types or edge_type_registry

    def get_node(self, node_id: UUID) -> Node:
        try:
            row = self._repo.get_node(node_id)
        except SQLAlchemyError as e:
            raise HTTPException(
                status_code=503,
                detail="Graph projection is not available. Load data and build graph tables first.",
            ) from e
        if row is None:
            raise HTTPException(status_code=404, detail="Node not found")

        try:
            deg = self._repo.get_degrees(node_id)
        except SQLAlchemyError as e:
            raise HTTPException(
                status_code=503,
                detail="Graph projection is not available. Load data and build graph tables first.",
            ) from e
        in_deg = int(deg.get("in_degree") or 0)
        out_deg = int(deg.get("out_degree") or 0)
        degrees = Degrees(in_degree=in_deg, out_degree=out_deg, total=in_deg + out_deg)

        return Node(
            id=row["node_id"],
            key=row["node_key"],
            type=row["node_type"],
            label=row["label"],
            attrs=row.get("attrs") or {},
            degrees=degrees,
        )

    def get_neighbors(
        self,
        *,
        node_id: UUID,
        direction: str,
        edge_type_ids: list[UUID] | None,
        include_granular: bool,
        limit: int,
    ) -> GraphPayload:
        # Resolve selected relationship IDs → stored edge_type codes.
        if edge_type_ids:
            selected: list[str] = []
            for edge_type_id in edge_type_ids:
                et = self._edge_types.get_by_id(edge_type_id)
                if et is None:
                    continue
                if not include_granular and et.is_granular:
                    continue
                selected.append(et.code)
            edge_type_codes = selected
        else:
            edge_type_codes = self._edge_types.filter_codes(include_granular=include_granular)

        try:
            edges_rows = self._repo.get_edges_for_node(
                node_id=node_id,
                direction=direction,
                edge_type_codes=edge_type_codes,
                limit=limit,
            )
        except SQLAlchemyError as e:
            raise HTTPException(
                status_code=503,
                detail="Graph projection is not available. Load data and build graph tables first.",
            ) from e

        node_ids: set[UUID] = {node_id}
        for e in edges_rows:
            node_ids.add(e["src_node_id"])
            node_ids.add(e["dst_node_id"])

        try:
            node_rows = self._repo.get_nodes_by_ids(list(node_ids))
        except SQLAlchemyError as e:
            raise HTTPException(
                status_code=503,
                detail="Graph projection is not available. Load data and build graph tables first.",
            ) from e
        nodes = [
            Node(
                id=r["node_id"],
                key=r["node_key"],
                type=r["node_type"],
                label=r["label"],
                attrs=r.get("attrs") or {},
                degrees=Degrees(),
            )
            for r in node_rows
        ]

        edges: list[Edge] = []
        for e in edges_rows:
            code = e["edge_type"]
            et = self._edge_types.get_by_code(code)
            type_id = et.id if et is not None else uuidlib.uuid5(EDGE_TYPE_NAMESPACE, code)

            edges.append(
                Edge(
                    id=e["edge_id"],
                    typeId=type_id,
                    typeCode=code,
                    src=e["src_node_id"],
                    dst=e["dst_node_id"],
                    evidence=e.get("evidence"),
                )
            )

        return GraphPayload(nodes=nodes, edges=edges)

    def get_subgraph(
        self,
        *,
        seed_node_ids: list[UUID],
        max_hops: int,
        edge_type_ids: list[UUID] | None,
        include_granular: bool,
        max_nodes: int,
        max_edges: int,
    ) -> GraphPayload:
        # Resolve relationship filter
        if edge_type_ids:
            selected: list[str] = []
            for edge_type_id in edge_type_ids:
                et = self._edge_types.get_by_id(edge_type_id)
                if et is None:
                    continue
                if not include_granular and et.is_granular:
                    continue
                selected.append(et.code)
            edge_type_codes = selected
        else:
            edge_type_codes = self._edge_types.filter_codes(include_granular=include_granular)

        if not edge_type_codes:
            node_rows = self._repo.get_nodes_by_ids(seed_node_ids[:max_nodes])
            nodes = [
                Node(
                    id=r["node_id"],
                    key=r["node_key"],
                    type=r["node_type"],
                    label=r["label"],
                    attrs=r.get("attrs") or {},
                    degrees=Degrees(),
                )
                for r in node_rows
            ]
            return GraphPayload(nodes=nodes, edges=[])

        try:
            edge_rows = self._repo.get_subgraph_edges(
                seed_node_ids=seed_node_ids,
                max_hops=max_hops,
                edge_type_codes=edge_type_codes,
                max_edges=max_edges,
            )
        except SQLAlchemyError as e:
            raise HTTPException(
                status_code=503,
                detail="Graph projection is not available. Load data and build graph tables first.",
            ) from e

        node_ids: list[UUID] = []
        seen: set[UUID] = set()
        for sid in seed_node_ids:
            if sid not in seen:
                node_ids.append(sid)
                seen.add(sid)
        for e in edge_rows:
            for nid in (e["src_node_id"], e["dst_node_id"]):
                if nid not in seen:
                    node_ids.append(nid)
                    seen.add(nid)
                if len(node_ids) >= max_nodes:
                    break
            if len(node_ids) >= max_nodes:
                break

        # Filter edges to included node_ids (in case we hit max_nodes)
        allowed = set(node_ids)
        filtered_edges = [e for e in edge_rows if e["src_node_id"] in allowed and e["dst_node_id"] in allowed]

        try:
            node_rows = self._repo.get_nodes_by_ids(node_ids)
        except SQLAlchemyError as e:
            raise HTTPException(
                status_code=503,
                detail="Graph projection is not available. Load data and build graph tables first.",
            ) from e

        nodes = [
            Node(
                id=r["node_id"],
                key=r["node_key"],
                type=r["node_type"],
                label=r["label"],
                attrs=r.get("attrs") or {},
                degrees=Degrees(),
            )
            for r in node_rows
        ]

        edges: list[Edge] = []
        for e in filtered_edges:
            code = e["edge_type"]
            et = self._edge_types.get_by_code(code)
            type_id = et.id if et is not None else uuidlib.uuid5(EDGE_TYPE_NAMESPACE, code)
            edges.append(
                Edge(
                    id=e["edge_id"],
                    typeId=type_id,
                    typeCode=code,
                    src=e["src_node_id"],
                    dst=e["dst_node_id"],
                    evidence=e.get("evidence"),
                )
            )

        return GraphPayload(nodes=nodes, edges=edges)

