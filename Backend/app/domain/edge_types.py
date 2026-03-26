from __future__ import annotations

import uuid
from dataclasses import dataclass


EDGE_TYPE_NAMESPACE = uuid.UUID("4c4d9c7f-8b3d-4f57-8c1d-5d7d1f0f2a11")


@dataclass(frozen=True)
class EdgeTypeDef:
    code: str
    display_name: str
    description: str
    src_node_type: str | None
    dst_node_type: str | None
    is_granular: bool
    group: str

    @property
    def id(self) -> uuid.UUID:
        # Deterministic UUID: stable across rebuilds and deployments.
        return uuid.uuid5(EDGE_TYPE_NAMESPACE, self.code)


EDGE_TYPES: list[EdgeTypeDef] = [
    EdgeTypeDef(
        code="PLACED_ORDER",
        display_name="Customer placed order",
        description="Customer placed a sales order",
        src_node_type="Customer",
        dst_node_type="SalesOrder",
        is_granular=False,
        group="o2c_flow",
    ),
    EdgeTypeDef(
        code="DELIVERED_AS",
        display_name="Sales order delivered as delivery",
        description="Sales order fulfilled by an outbound delivery",
        src_node_type="SalesOrder",
        dst_node_type="OutboundDelivery",
        is_granular=False,
        group="o2c_flow",
    ),
    EdgeTypeDef(
        code="HAS_ITEM",
        display_name="Document has item",
        description="Parent document contains line-items",
        src_node_type=None,
        dst_node_type=None,
        is_granular=True,
        group="o2c_flow",
    ),
    EdgeTypeDef(
        code="FULFILLED_BY",
        display_name="Order item fulfilled by delivery item",
        description="Sales order item fulfilled by outbound delivery item",
        src_node_type="SalesOrderItem",
        dst_node_type="OutboundDeliveryItem",
        is_granular=True,
        group="o2c_flow",
    ),
    EdgeTypeDef(
        code="BILLED_BY",
        display_name="Delivery item billed by billing item",
        description="Outbound delivery item billed by billing document item",
        src_node_type="OutboundDeliveryItem",
        dst_node_type="BillingDocumentItem",
        is_granular=True,
        group="o2c_flow",
    ),
    EdgeTypeDef(
        code="BILLED_AS",
        display_name="Delivery billed as billing document",
        description="Outbound delivery billed into a billing document",
        src_node_type="OutboundDelivery",
        dst_node_type="BillingDocument",
        is_granular=False,
        group="o2c_flow",
    ),
    EdgeTypeDef(
        code="POSTED_AS",
        display_name="Billing posted as journal entry",
        description="Billing document posted into accounting/journal entry",
        src_node_type="BillingDocument",
        dst_node_type="JournalEntryItemAR",
        is_granular=False,
        group="finance",
    ),
    EdgeTypeDef(
        code="CLEARED_BY",
        display_name="AR item cleared by payment",
        description="Journal entry AR item cleared by a payment/clearing document",
        src_node_type="JournalEntryItemAR",
        dst_node_type="Payment",
        is_granular=False,
        group="finance",
    ),
    EdgeTypeDef(
        code="REFERS_TO_PRODUCT",
        display_name="Item refers to product",
        description="Document item references a product/material",
        src_node_type=None,
        dst_node_type="Product",
        is_granular=True,
        group="master_data",
    ),
]

