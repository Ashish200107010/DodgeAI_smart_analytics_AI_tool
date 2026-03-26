from __future__ import annotations

import re


_DOC_ID_RE = re.compile(r"\b\d{6,10}\b")


def is_in_domain(message: str) -> bool:
    m = (message or "").lower()

    # Numeric document IDs (sales order, delivery, billing, accounting docs).
    if _DOC_ID_RE.search(m):
        return True

    keywords = [
        "order",
        "sales order",
        "delivery",
        "outbound",
        "billing",
        "invoice",
        "payment",
        "journal",
        "accounting",
        "customer",
        "business partner",
        "product",
        "material",
        "plant",
    ]
    return any(k in m for k in keywords)


def rejection_message() -> str:
    return "This system is designed to answer questions related to the provided dataset only."

