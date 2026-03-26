from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class Degrees(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    in_degree: int = Field(0, serialization_alias="in")
    out_degree: int = Field(0, serialization_alias="out")
    total: int = 0


class Node(BaseModel):
    id: UUID
    key: str
    type: str
    label: str
    attrs: dict[str, Any] = Field(default_factory=dict)
    degrees: Degrees = Field(default_factory=Degrees)


class Edge(BaseModel):
    id: UUID
    typeId: UUID
    typeCode: str
    src: UUID
    dst: UUID
    evidence: dict[str, Any] | None = None


class GraphPayload(BaseModel):
    nodes: list[Node]
    edges: list[Edge]


class SubgraphRequest(BaseModel):
    seedNodeIds: list[UUID] = Field(min_length=1)
    maxHops: int = Field(default=2, ge=0, le=6)
    edgeTypeIds: list[UUID] | None = None
    includeGranular: bool = True
    maxNodes: int = Field(default=500, ge=1, le=5000)
    maxEdges: int = Field(default=2000, ge=1, le=20000)

