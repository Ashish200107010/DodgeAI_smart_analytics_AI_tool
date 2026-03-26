from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class UIContext(BaseModel):
    focusedNodeId: UUID | None = None
    activeEdgeTypeIds: list[UUID] | None = None
    hideGranularOverlay: bool | None = None


class ChatQueryRequest(BaseModel):
    message: str = Field(min_length=1)
    uiContext: UIContext | None = None


class TabularData(BaseModel):
    columns: list[str]
    rows: list[dict[str, Any]]
    rowCount: int


class Highlights(BaseModel):
    focusNodeId: UUID | None = None
    highlightNodeIds: list[UUID] = Field(default_factory=list)
    highlightEdgeIds: list[UUID] = Field(default_factory=list)


class ChatQueryResponse(BaseModel):
    answer: str
    rejected: bool = False
    rejectionReason: str | None = None

    data: TabularData | None = None
    highlights: Highlights | None = None

