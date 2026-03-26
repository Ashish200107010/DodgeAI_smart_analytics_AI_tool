from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import DBConn, EdgeTypes
from app.api.schemas.chat import ChatQueryRequest, ChatQueryResponse
from app.chat.service import ChatService


router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/query", response_model=ChatQueryResponse)
def query_chat(req: ChatQueryRequest, conn: DBConn, edge_types: EdgeTypes) -> ChatQueryResponse:
    return ChatService(conn, edge_types=edge_types).query(req)

