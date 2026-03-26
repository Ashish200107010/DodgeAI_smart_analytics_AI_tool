from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel


class EdgeType(BaseModel):
    id: UUID
    code: str
    displayName: str
    description: str
    srcNodeType: str | None
    dstNodeType: str | None
    isGranular: bool
    group: str

