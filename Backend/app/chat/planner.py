from __future__ import annotations

import json
import re
from typing import Any

from pydantic import BaseModel, Field

from app.core.config import settings
from app.llm.client import OpenAIJsonClient


class QueryPlan(BaseModel):
    template: str
    params: dict[str, Any] = Field(default_factory=dict)
    limit: int = 10


class QueryPlanner:
    def plan(self, message: str) -> QueryPlan | None:  # pragma: no cover (interface)
        raise NotImplementedError


class RuleBasedPlanner(QueryPlanner):
    _billing_doc_re = re.compile(r"\b(\d{8})\b")

    def plan(self, message: str) -> QueryPlan | None:
        m = (message or "").lower()
        billing_doc_match = self._billing_doc_re.search(message or "")

        if billing_doc_match and ("journal" in m or "accounting" in m):
            return QueryPlan(
                template="billing_document_to_journal_entry",
                params={"billing_document": billing_doc_match.group(1)},
                limit=10,
            )

        if "highest" in m and ("billing" in m or "invoice" in m) and ("product" in m or "material" in m):
            return QueryPlan(
                template="top_products_by_billing_docs",
                params={},
                limit=10,
            )

        if "broken" in m or "incomplete" in m:
            return QueryPlan(
                template="broken_flows",
                params={},
                limit=50,
            )

        return None


class OpenAIPlanner(QueryPlanner):
    def __init__(self, client: OpenAIJsonClient) -> None:
        self._client = client

    def plan(self, message: str) -> QueryPlan | None:
        templates = [
            {
                "template": "billing_document_to_journal_entry",
                "description": "Given a billing document id, find the linked accounting/journal entry.",
                "params": {"billing_document": "string"},
            },
            {
                "template": "top_products_by_billing_docs",
                "description": "Which products have the highest number of billing documents.",
                "params": {},
            },
            {
                "template": "broken_flows",
                "description": "Find sales orders with incomplete flows (delivered not billed, billed without delivery).",
                "params": {},
            },
        ]

        system = (
            "You are a data assistant for an SAP Order-to-Cash dataset. "
            "Choose ONE template and output a JSON object with keys: template, params, limit. "
            "Use only the provided templates. If none match, output {\"template\": \"none\"}."
        )
        user = json.dumps({"message": message, "templates": templates})

        obj = self._client.json_object(system=system, user=user)
        if not isinstance(obj, dict):
            return None
        if obj.get("template") in (None, "", "none"):
            return None
        try:
            return QueryPlan.model_validate(obj)
        except Exception:
            return None


def get_planner() -> QueryPlanner:
    # Prefer LLM planning if configured; otherwise fall back to deterministic rules.
    if settings.openai_api_key:
        return OpenAIPlanner(OpenAIJsonClient(api_key=settings.openai_api_key, model=settings.openai_model))
    return RuleBasedPlanner()

