from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.engine import Connection
from sqlalchemy.exc import SQLAlchemyError

from app.api.schemas.chat import ChatQueryRequest, ChatQueryResponse, Highlights, TabularData
from app.chat.guardrails import is_in_domain, rejection_message
from app.chat.planner import get_planner
from app.chat.repository import ChatRepository
from app.domain.registry import EdgeTypeRegistry, edge_type_registry


class ChatService:
    def __init__(self, conn: Connection, *, edge_types: EdgeTypeRegistry | None = None) -> None:
        self._repo = ChatRepository(conn)
        self._planner = get_planner()
        self._edge_types = edge_types or edge_type_registry

    def query(self, req: ChatQueryRequest) -> ChatQueryResponse:
        message = req.message.strip()

        if not is_in_domain(message):
            return ChatQueryResponse(
                answer=rejection_message(),
                rejected=True,
                rejectionReason="out_of_domain",
            )

        plan = self._planner.plan(message)
        if plan is None:
            return ChatQueryResponse(
                answer="I can’t map that question to a supported dataset query yet.",
                rejected=True,
                rejectionReason="unsupported_query",
            )

        params: dict[str, Any] = dict(plan.params)
        params.setdefault("limit", plan.limit)

        try:
            rows = self._repo.run_template(plan.template, params)
        except SQLAlchemyError as e:
            return ChatQueryResponse(
                answer="Dataset/graph tables are not available yet. Load the dataset into Postgres and rebuild the graph projection.",
                rejected=True,
                rejectionReason="data_not_loaded",
            )
        data = TabularData(
            columns=list(rows[0].keys()) if rows else [],
            rows=rows,
            rowCount=len(rows),
        )

        answer = self._render_answer(plan.template, params, rows)
        highlights = self._extract_highlights(rows)

        return ChatQueryResponse(
            answer=answer,
            rejected=False,
            data=data,
            highlights=highlights,
        )

    def _render_answer(self, template: str, params: dict[str, Any], rows: list[dict[str, Any]]) -> str:
        if not rows:
            return "No results found in the dataset for that query."

        if template == "billing_document_to_journal_entry":
            billing = params.get("billing_document")
            accounting_doc = rows[0].get("accountingDocument") or rows[0].get("accounting_document")
            if accounting_doc:
                return f"The journal entry number linked to billing document {billing} is {accounting_doc}."
            return f"I found billing document {billing}, but no linked journal entry was returned."

        if template == "top_products_by_billing_docs":
            top = rows[:5]
            lines = []
            for r in top:
                product = r.get("product") or r.get("material")
                cnt = r.get("billingDocumentCount") or r.get("billing_document_count")
                lines.append(f"- {product}: {cnt}")
            return "Top products by number of billing documents:\n" + "\n".join(lines)

        if template == "broken_flows":
            return f"Found {len(rows)} sales orders with incomplete flows (sample shown in the table)."

        return "Query executed successfully."

    def _extract_highlights(self, rows: list[dict[str, Any]]) -> Highlights | None:
        if not rows:
            return None

        node_ids: list[UUID] = []
        edge_ids: list[UUID] = []

        for r in rows:
            for k, v in r.items():
                if v is None:
                    continue
                if k.lower().endswith("nodeid"):
                    try:
                        node_ids.append(UUID(str(v)))
                    except Exception:
                        pass
                if k.lower().endswith("edgeid"):
                    try:
                        edge_ids.append(UUID(str(v)))
                    except Exception:
                        pass

        if not node_ids and not edge_ids:
            return None

        focus = node_ids[0] if node_ids else None
        return Highlights(
            focusNodeId=focus,
            highlightNodeIds=list(dict.fromkeys(node_ids)),
            highlightEdgeIds=list(dict.fromkeys(edge_ids)),
        )

