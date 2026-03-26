## Schema Design Plan (Option B)

This document defines the planned **relational schema** (raw tables) and the **graph projection schema** (`graph_nodes`, `graph_edges`) for the SAP O2C dataset.

Goals:
- Preserve the dataset **as provided** (raw tables are the source of truth).
- Enable **fast graph exploration** (neighbors/paths) via `graph_edges`.
- Keep answers **grounded** (every graph node/edge can be traced back to raw rows).

---

## Conventions

- **Schemas**
  - `raw.*`: tables loaded from the JSONL folders (source of truth)
  - `graph.*`: derived projection for fast traversal
- **IDs / keys**
  - Use the dataset’s natural keys as PKs where they exist (e.g., `salesOrder`, `billingDocument`).
  - For composite keys (items/line-items), use composite PKs (e.g., `(salesOrder, salesOrderItem)`).
- **Types**
  - Keep key fields as `text` (SAP-like IDs can be numeric-looking but are identifiers).
  - Amount fields: `numeric`
  - Dates/timestamps: `timestamptz` (dataset uses `...Z`)
  - “Time objects” like `{hours, minutes, seconds}`: store as `time` in `raw` if convenient, otherwise keep in payload.
- **Optional “payload”**
  - Each `raw.*` table may include `payload jsonb` to preserve the full original record (useful for UI drilldown without adding many columns).
  - We still **promote** relationship keys and common filter fields to typed columns for indexing and joins.

---

## 1) Raw tables (source of truth)

Below are the entities (dataset folders) and the **member variables** we should persist as first-class columns, with reasoning.
Anything not listed can remain in `payload` (still accessible if needed).

### 1.1 `raw.sales_order_headers`

- **Primary key**
  - `sales_order` (`salesOrder`): **unique per order header** in the provided dataset (1 row per order), and the join anchor for the entire O2C flow.
  - Note: you will see `salesOrder` repeated in `raw.sales_order_items` / `raw.sales_order_schedule_lines` (one-to-many), and in any SQL result that joins headers to those tables (the header row gets repeated per child row).
- **Sales area / segmentation**
  - `sales_order_type` (`salesOrderType`): filter by order process.
  - `sales_organization` (`salesOrganization`): analytics by org.
  - `distribution_channel` (`distributionChannel`): channel slice.
  - `division` (`organizationDivision`): product/division slice.
  - `sales_group` (`salesGroup`), `sales_office` (`salesOffice`): org drilldowns.
- **Customer**
  - `sold_to_party` (`soldToParty`): link to `raw.business_partners` (“Customer”).
- **Dates**
  - `creation_date` (`creationDate`): order timeline + “late/old” detection.
  - `pricing_date` (`pricingDate`): pricing context.
  - `requested_delivery_date` (`requestedDeliveryDate`): expected fulfillment date.
  - `last_change_datetime` (`lastChangeDateTime`): recency / churn.
- **Amounts**
  - `total_net_amount` (`totalNetAmount`): order value analytics.
  - `transaction_currency` (`transactionCurrency`): currency handling.
- **Statuses / blocks (broken-flow detection)**
  - `overall_delivery_status` (`overallDeliveryStatus`): delivered vs not.
  - `overall_billing_status` (`overallOrdReltdBillgStatus`): billed vs not.
  - `header_billing_block_reason` (`headerBillingBlockReason`): “why not billed”.
  - `delivery_block_reason` (`deliveryBlockReason`): “why not delivered”.
  - `total_credit_check_status` (`totalCreditCheckStatus`): credit-related issues.
- **Logistics terms**
  - `incoterms_classification` (`incotermsClassification`): shipping terms.
  - `incoterms_location1` (`incotermsLocation1`): shipping location.
  - `customer_payment_terms` (`customerPaymentTerms`): payment behavior segmentation.
- **Provenance (debug/UI)**
  - `created_by_user` (`createdByUser`): explains outliers and data lineage.

### 1.2 `raw.sales_order_items`

- **Primary key**
  - `(sales_order, sales_order_item)` (`salesOrder`, `salesOrderItem`): unique item.
  - Note: `salesOrder` alone is **not unique** here (1-to-many from order → items). Uniqueness is at `(salesOrder, salesOrderItem)`.
- **Item semantics**
  - `item_category` (`salesOrderItemCategory`): determines downstream behavior.
  - `material` (`material`): link to product master.
  - `material_group` (`materialGroup`): product grouping analytics.
- **Quantities**
  - `requested_quantity` (`requestedQuantity`): ordered quantity.
  - `requested_quantity_unit` (`requestedQuantityUnit`): unit correctness.
- **Amounts**
  - `net_amount` (`netAmount`): revenue by product/order.
  - `transaction_currency` (`transactionCurrency`): currency alignment with header.
- **Fulfillment attributes**
  - `production_plant` (`productionPlant`): supply-side analytics.
  - `storage_location` (`storageLocation`): inventory location analytics.
- **Broken-flow reasons**
  - `rejection_reason` (`salesDocumentRjcnReason`): item rejected.
  - `item_billing_block_reason` (`itemBillingBlockReason`): item-level billing block.

### 1.3 `raw.sales_order_schedule_lines`

- **Primary key**
  - `(sales_order, sales_order_item, schedule_line)` (`salesOrder`, `salesOrderItem`, `scheduleLine`)
- **Commitment**
  - `confirmed_delivery_date` (`confirmedDeliveryDate`): expected ship date.
  - `confirmed_qty` (`confdOrderQtyByMatlAvailCheck`): ATP/availability outcome.
  - `order_quantity_unit` (`orderQuantityUnit`): unit correctness for qty.

### 1.4 `raw.outbound_delivery_headers`

- **Primary key**
  - `delivery_document` (`deliveryDocument`)
- **Dates/times**
  - `creation_date` (`creationDate`), `creation_time` (`creationTime`): delivery creation timeline.
  - `actual_goods_movement_date` (`actualGoodsMovementDate`), `actual_goods_movement_time` (`actualGoodsMovementTime`): actual fulfillment timestamp.
  - `last_change_date` (`lastChangeDate`): recency.
- **Operational location**
  - `shipping_point` (`shippingPoint`): logistics node (used in “delivery → plant” style queries).
- **Statuses / blocks**
  - `overall_goods_movement_status` (`overallGoodsMovementStatus`): shipped vs not.
  - `overall_picking_status` (`overallPickingStatus`): warehouse readiness.
  - `overall_proof_of_delivery_status` (`overallProofOfDeliveryStatus`): POD completion.
  - `hdr_general_incompletion_status` (`hdrGeneralIncompletionStatus`): completeness check.
  - `delivery_block_reason` (`deliveryBlockReason`), `header_billing_block_reason` (`headerBillingBlockReason`): blockage reasons.

### 1.5 `raw.outbound_delivery_items`

- **Primary key**
  - `(delivery_document, delivery_document_item)` (`deliveryDocument`, `deliveryDocumentItem`)
- **Link back to sales order**
  - `reference_sd_document` (`referenceSdDocument`): links delivery item → sales order.
  - `reference_sd_document_item` (`referenceSdDocumentItem`): links delivery item → sales order item.
- **Quantities**
  - `actual_delivery_quantity` (`actualDeliveryQuantity`): fulfillment quantity.
  - `delivery_quantity_unit` (`deliveryQuantityUnit`): unit correctness.
- **Location**
  - `plant` (`plant`): supports “Delivery → Plant” relationship.
  - `storage_location` (`storageLocation`): inventory location.
- **Other**
  - `batch` (`batch`): batch tracking (if used).
  - `item_billing_block_reason` (`itemBillingBlockReason`): item-level billing block.
  - `last_change_date` (`lastChangeDate`): recency/debug.

### 1.6 `raw.billing_document_headers`

- **Primary key**
  - `billing_document` (`billingDocument`)
- **Document semantics**
  - `billing_document_type` (`billingDocumentType`): billing process type.
- **Dates/times**
  - `billing_document_date` (`billingDocumentDate`): billing effective date.
  - `creation_date` (`creationDate`), `creation_time` (`creationTime`): creation timeline.
  - `last_change_datetime` (`lastChangeDateTime`): recency.
- **Cancellation**
  - `is_cancelled` (`billingDocumentIsCancelled`): flow correctness.
  - `cancelled_billing_document` (`cancelledBillingDocument`): link to cancellation chain.
- **Amounts**
  - `total_net_amount` (`totalNetAmount`): billing value.
  - `transaction_currency` (`transactionCurrency`): currency.
- **Accounting linkage**
  - `company_code` (`companyCode`): finance org key.
  - `fiscal_year` (`fiscalYear`): accounting join key.
  - `accounting_document` (`accountingDocument`): links to journal entry items.
- **Customer**
  - `sold_to_party` (`soldToParty`): link to customer.

### 1.7 `raw.billing_document_items`

- **Primary key**
  - `(billing_document, billing_document_item)` (`billingDocument`, `billingDocumentItem`)
- **Product & quantities**
  - `material` (`material`): supports product ↔ billing queries.
  - `billing_quantity` (`billingQuantity`), `billing_quantity_unit` (`billingQuantityUnit`): billed qty.
- **Amounts**
  - `net_amount` (`netAmount`): line value.
  - `transaction_currency` (`transactionCurrency`): currency.
- **Reference to preceding SD document**
  - `reference_sd_document` (`referenceSdDocument`): typically links billing item → delivery document in this dataset.
  - `reference_sd_document_item` (`referenceSdDocumentItem`): links billing item → delivery item.

### 1.8 `raw.billing_document_cancellations`

- Same core fields as `raw.billing_document_headers`.
- Useful for quickly enumerating cancellations without filtering the entire header set.

### 1.9 `raw.journal_entry_items_accounts_receivable`

- **Primary key**
  - `(company_code, fiscal_year, accounting_document, accounting_document_item)`
- **Reference back to billing**
  - `reference_document` (`referenceDocument`): links accounting → billing document.
- **Customer**
  - `customer` (`customer`): links accounting → customer.
- **Dates**
  - `posting_date` (`postingDate`), `document_date` (`documentDate`): accounting timeline.
  - `last_change_datetime` (`lastChangeDateTime`): recency/debug.
- **Amounts**
  - `amount_txn_currency` (`amountInTransactionCurrency`), `transaction_currency` (`transactionCurrency`)
  - `amount_cc_currency` (`amountInCompanyCodeCurrency`), `company_code_currency` (`companyCodeCurrency`)
  - Reason: supports accurate multi-currency answers.
- **Accounting dimensions**
  - `gl_account` (`glAccount`): account analysis.
  - `profit_center` (`profitCenter`), `cost_center` (`costCenter`): org analytics.
  - `accounting_document_type` (`accountingDocumentType`): doc classification.
  - `financial_account_type` (`financialAccountType`): AR/other.
- **Clearing (payment linkage)**
  - `clearing_date` (`clearingDate`)
  - `clearing_accounting_document` (`clearingAccountingDocument`)
  - `clearing_doc_fiscal_year` (`clearingDocFiscalYear`)
  - Reason: connects invoice/AR items to payment clearing docs.

### 1.10 `raw.payments_accounts_receivable`

- **Primary key**
  - `(company_code, fiscal_year, accounting_document, accounting_document_item)` (same key shape as AR items)
- **Clearing linkage**
  - `clearing_date`, `clearing_accounting_document`, `clearing_doc_fiscal_year`: anchors “payment” nodes/edges.
- **Amounts**
  - same amount/currency fields: payment analytics and reconciliation.
- **Optional references**
  - `invoice_reference`, `invoice_reference_fiscal_year`: when present, direct invoice linkage.
  - `sales_document`, `sales_document_item`: when present, direct sales doc linkage.
- **Customer**
  - `customer`: payer/customer analysis.

### 1.11 `raw.business_partners` (Customer master)

- **Primary key**
  - `business_partner` (`businessPartner`) (same value as `customer` in sample data)
- **Identity / display**
  - `business_partner_name` (`businessPartnerName`)
  - `business_partner_full_name` (`businessPartnerFullName`)
  - `business_partner_category` (`businessPartnerCategory`): person vs org.
  - `business_partner_grouping` (`businessPartnerGrouping`): segmentation.
  - `first_name`, `last_name`, `organization_bp_name1/2`: display and search.
- **Lifecycle**
  - `creation_date`, `creation_time`, `created_by_user`: lineage.
  - `last_change_date`: recency.
  - `is_blocked` (`businessPartnerIsBlocked`): guardrail/filtering.
  - `is_marked_for_archiving` (`isMarkedForArchiving`): guardrail/filtering.

### 1.12 `raw.business_partner_addresses`

- **Primary key**
  - `(business_partner, address_id, validity_start_date)` (supports historical addresses)
- **Validity**
  - `validity_start_date`, `validity_end_date`: time-bounded truth.
- **Address identity**
  - `address_uuid`: stable unique reference.
  - `address_id`: join key (also used by plants).
- **Location**
  - `street_name`, `city_name`, `region`, `country`, `postal_code`: UI display and geo filters.
  - `transport_zone`, `tax_jurisdiction`: logistics/tax analytics (if asked).
  - `address_time_zone`: date/time interpretation (edge cases).
- **PO box fields**
  - Keep as-is for completeness; useful if dataset uses PO boxes.

### 1.13 `raw.customer_company_assignments`

- **Primary key**
  - `(customer, company_code)`
- **Finance integration**
  - `reconciliation_account`: explains accounting postings.
  - `payment_terms`, `payment_methods_list`, `payment_blocking_reason`: payment behavior + exceptions.
  - `alternative_payer_account`: payer relationships.
- **Lifecycle**
  - `deletion_indicator`: active/inactive customers.
  - `customer_account_group`: segmentation.
- **Accounting clerk fields**
  - Useful for “who owns this customer” operational questions.

### 1.14 `raw.customer_sales_area_assignments`

- **Primary key**
  - `(customer, sales_organization, distribution_channel, division)`
- **Commercial terms**
  - `currency`: pricing currency.
  - `customer_payment_terms`: payment terms at sales-area level.
  - `incoterms_classification`, `incoterms_location1`: shipping terms.
  - `shipping_condition`, `delivery_priority`: logistics service levels.
- **Controls**
  - `billing_is_blocked_for_customer`: why billing can’t proceed.
  - `complete_delivery_is_defined`: partial vs complete delivery rules.
  - `credit_control_area`: credit management dimension.
- **Org routing**
  - `sales_group`, `sales_office`, `supplying_plant`, `sales_district`: org/fulfillment analysis.
- **Pricing mechanics**
  - `exchange_rate_type`: currency conversion rules.

### 1.15 `raw.products`

- **Primary key**
  - `product` (`product`) (joins to `material` fields)
- **Classification**
  - `product_type` (`productType`)
  - `product_group` (`productGroup`) (aligns with `materialGroup`)
  - `division` (`division`)
  - `industry_sector` (`industrySector`)
- **Units/weights**
  - `base_unit` (`baseUnit`): quantity interpretation.
  - `gross_weight`, `net_weight`, `weight_unit`: logistics analytics.
- **Lifecycle**
  - `creation_date`, `created_by_user`, `last_change_date/time`: lineage.
  - `is_marked_for_deletion`: guardrail/filtering.
  - `product_old_id`: cross-reference.
- **Cross-plant status**
  - `cross_plant_status`, `cross_plant_status_validity_date`: availability constraints.

### 1.16 `raw.product_descriptions`

- **Primary key**
  - `(product, language)`
- **Search / UX**
  - `product_description`: used for UI labels and natural language matching (“charcoal gang” → product id).

### 1.17 `raw.plants`

- **Primary key**
  - `plant` (`plant`)
- **Identity / routing**
  - `plant_name` (`plantName`): UI display.
  - `sales_organization`, `distribution_channel`, `division`: org routing context.
- **Address linkage**
  - `address_id` (`addressId`): link plant → address.
- **Lifecycle**
  - `is_marked_for_archiving`: guardrail/filtering.
- **Other**
  - `valuation_area`, `plant_customer`, `plant_supplier`, `factory_calendar`: supports deeper ops questions if asked.

### 1.18 `raw.product_plants`

- **Primary key**
  - `(product, plant)`
- **Planning / finance**
  - `profit_center`: profit attribution.
  - `mrp_type`: planning behavior.
  - `availability_check_type`: ATP behavior.
- **Origin**
  - `country_of_origin`, `region_of_origin`: compliance/analytics.
- **Inventory management**
  - `production_invtry_managed_loc`: inventory management location.

### 1.19 `raw.product_storage_locations`

- **Primary key**
  - `(product, plant, storage_location)`
- **Inventory controls**
  - `physical_inventory_block_ind`: explains inventory locks.
  - `date_of_last_posted_count`: inventory freshness.

---

## 2) Graph projection schema (fast traversal)

### 2.1 `graph.graph_nodes`

Store one row per business entity we want to visualize/traverse.

Member variables:
- `node_id` (uuid, PK)
  - **Why**: stable internal identifier used by the UI/API and referenced by edges; compact and index-friendly.
  - **Generation**: UUIDv4 is fine for this assignment; if you want IDs stable across rebuilds, generate a deterministic UUIDv5 from `node_key`.
- `node_key` (text, unique)
  - **Why**: deterministic, human-readable key derived from business identifiers; used for debugging and for (re)building the projection consistently.
  - **Format**: `<NodeType>:<business_key>` (for composite keys, concatenate with `|`).
- `node_type` (text)
  - **Why**: enables type-specific rendering, filtering, and guardrails.
- `raw_table` (text, nullable)
  - **Why**: trace node back to its source-of-truth table.
- `raw_pk` (jsonb, nullable)
  - **Why**: traceability to a specific raw row (or composite PK).
- `label` (text)
  - **Why**: what the UI shows on the node (e.g., `SO 740506`, `Billing 90504248`).
- `attrs` (jsonb)
  - **Why**: small set of denormalized fields for fast UI tooltips and common filtering (dates, amounts, statuses, names).
  - **Rule**: keep it minimal; raw tables remain the truth.

Recommended indexes:
- PK on `node_id`
- Unique index on `node_key`
- `(node_type)`

### 2.2 `graph.graph_edges`

Store typed relationships as an adjacency list.

Member variables:
- `edge_id` (uuid, PK)
  - **Why**: stable internal identifier for UI selection/highlighting/debug; UUID keeps ID style consistent across the graph model.
  - **Generation**: UUIDv4 is fine for this assignment; for stable IDs across rebuilds, generate deterministic UUIDv5 from `(edge_type, src_node_id, dst_node_id)` (or from a deterministic `edge_key`).
- `edge_key` (text, unique)
  - **Why**: deterministic, human-readable key derived from business semantics; useful for debugging and for consistent rebuilds.
  - **Format**: `<edge_type>:<src_node_key>-><dst_node_key>` (or `<edge_type>:<src_node_id>-><dst_node_id>` if you prefer UUID-only keys).
- `src_node_id` (uuid, FK → `graph_nodes.node_id`)
- `dst_node_id` (uuid, FK → `graph_nodes.node_id`)
  - **Why**: constant-time neighbor expansion.
- `edge_type` (text)
  - **Why**: semantics (“HAS_ITEM”, “BILLED_BY”, …) for traversal and filtering.
- `evidence` (jsonb, nullable)
  - **Why**: shows *how* we connected the nodes (which raw keys/columns matched); helpful for grounding and debugging without a full telemetry system.

Recommended constraints/indexes:
- Unique constraint on `(src_node_id, edge_type, dst_node_id)` to prevent duplicates.
- Unique index on `edge_key`
- Indexes:
  - `(src_node_id, edge_type)`
  - `(dst_node_id, edge_type)`
  - `(edge_type)`

UI-driven notes:
- The “**Mapping → relationship**” selector in the UI is driven by `edge_type` values (and metadata for display names/descriptions).
- “**Hide Granular Overlay**” can be implemented by tagging certain `edge_type`s as `is_granular=true` in the domain map and filtering them out in graph queries.
- Chat responses should return **`node_id` UUIDs** to highlight/focus nodes after answering (grounded in query results).

---

## 3) Node types (entities) and the fields we should expose

These are the graph-visible entities; each maps to raw rows via `raw_table/raw_pk`.

### Sales Order (`SalesOrder`)

- **Business key**: `salesOrder`
- **Useful member variables (in `attrs`)**
  - `salesOrganization`, `distributionChannel`, `division`: common filters.
  - `soldToParty`: connect to customer.
  - `creationDate`, `requestedDeliveryDate`: timeline + SLA checks.
  - `totalNetAmount`, `transactionCurrency`: “top value” queries.
  - `overallDeliveryStatus`, `overallOrdReltdBillgStatus`: broken-flow detection.

### Sales Order Item (`SalesOrderItem`)

- **Business key**: `(salesOrder, salesOrderItem)`
- **Useful member variables**
  - `material`: connect to product.
  - `requestedQuantity`, `requestedQuantityUnit`: quantity analysis.
  - `netAmount`, `transactionCurrency`: line value.
  - `productionPlant`, `storageLocation`: supply chain context.
  - `salesDocumentRjcnReason`, `itemBillingBlockReason`: explain incomplete flows.

### Schedule Line (`ScheduleLine`)

- **Business key**: `(salesOrder, salesOrderItem, scheduleLine)`
- **Useful member variables**
  - `confirmedDeliveryDate`, `confdOrderQtyByMatlAvailCheck`: promise dates/quantities.

### Outbound Delivery (`OutboundDelivery`)

- **Business key**: `deliveryDocument`
- **Useful member variables**
  - `creationDate`, `actualGoodsMovementDate`: delivery timeline.
  - `shippingPoint`: logistics filter.
  - `overallGoodsMovementStatus`, `overallPickingStatus`: completeness checks.

### Outbound Delivery Item (`OutboundDeliveryItem`)

- **Business key**: `(deliveryDocument, deliveryDocumentItem)`
- **Useful member variables**
  - `referenceSdDocument`, `referenceSdDocumentItem`: trace back to sales order item.
  - `actualDeliveryQuantity`, `deliveryQuantityUnit`: fulfillment quantity.
  - `plant`, `storageLocation`: “delivery → plant” relationship.

### Billing Document (`BillingDocument`)

- **Business key**: `billingDocument`
- **Useful member variables**
  - `billingDocumentDate`, `billingDocumentType`: billing timeline/type.
  - `billingDocumentIsCancelled`, `cancelledBillingDocument`: cancellation flows.
  - `totalNetAmount`, `transactionCurrency`: billing value.
  - `companyCode`, `fiscalYear`, `accountingDocument`: links to accounting.
  - `soldToParty`: customer linkage.

### Billing Document Item (`BillingDocumentItem`)

- **Business key**: `(billingDocument, billingDocumentItem)`
- **Useful member variables**
  - `material`: supports “products with most billing docs”.
  - `billingQuantity`, `billingQuantityUnit`: quantities.
  - `netAmount`, `transactionCurrency`: line value.
  - `referenceSdDocument`, `referenceSdDocumentItem`: links to delivery item.

### Accounting Document (`AccountingDocument`)

Derived from `(companyCode, fiscalYear, accountingDocument)` using:
- `raw.billing_document_headers.accountingDocument`
- `raw.journal_entry_items_accounts_receivable.accountingDocument`

Useful member variables:
- `companyCode`, `fiscalYear`, `accountingDocumentType` (if available): finance context.
- `postingDate`, `documentDate`: accounting timeline.

### Journal Entry Item (AR) (`JournalEntryItemAR`)

- **Business key**: `(companyCode, fiscalYear, accountingDocument, accountingDocumentItem)`
- **Useful member variables**
  - `referenceDocument`: links to billing document.
  - `customer`: customer linkage.
  - `amountInTransactionCurrency`, `transactionCurrency`: amounts.
  - `clearingAccountingDocument`, `clearingDate`: payment linkage.

### Payment / Clearing Document (`Payment`)

Typically modeled as `(companyCode, clearingDocFiscalYear, clearingAccountingDocument)` using clearing fields from:
- `raw.journal_entry_items_accounts_receivable`
- `raw.payments_accounts_receivable`

Useful member variables:
- `clearingDate`: payment date.
- Aggregated amounts by clearing document (computed when building nodes): payment totals.
- `customer` (when available): payer linkage.

### Customer (`Customer`)

- **Business key**: `businessPartner`
- **Useful member variables**
  - `businessPartnerName`/`FullName`: UI + NL search.
  - `businessPartnerCategory`, `Grouping`: segmentation.
  - `isBlocked`, `isMarkedForArchiving`: guardrails / filtering.

### Address (`Address`)

- **Business key**: prefer `addressUuid` when available, else `addressId`.
- **Useful member variables**
  - `streetName`, `cityName`, `region`, `country`, `postalCode`: UI + geo filters.
  - `validityStartDate`, `validityEndDate`: correct “as of” behavior.

### Product (`Product`)

- **Business key**: `product`
- **Useful member variables**
  - `productDescription` (via `raw.product_descriptions`): UI label + NL matching.
  - `productType`, `productGroup`, `baseUnit`: classification and unit semantics.
  - `isMarkedForDeletion`: guardrails/filtering.

### Plant (`Plant`)

- **Business key**: `plant` (string; may include codes not present in `raw.plants`)
- **Useful member variables**
  - `plantName` when known (from `raw.plants`), else show code-only.
  - `addressId` (when known): link to address.

### Storage Location (`StorageLocation`) (optional node type)

- **Business key**: `(plant, storageLocation)`
- **Useful member variables**
  - supports inventory/location exploration and linking to product storage.

---

## 4) Edge types (relationships we will materialize)

Core O2C flow:
- `Customer` → `SalesOrder` (`PLACED_ORDER`) via `soldToParty`
- `SalesOrder` → `SalesOrderItem` (`HAS_ITEM`)
- `SalesOrderItem` → `ScheduleLine` (`HAS_SCHEDULE_LINE`)
- `SalesOrderItem` → `OutboundDeliveryItem` (`FULFILLED_BY`) via `outbound_delivery_items.referenceSdDocument(+Item)`
- `OutboundDelivery` → `OutboundDeliveryItem` (`HAS_ITEM`)
- `BillingDocument` → `BillingDocumentItem` (`HAS_ITEM`)
- `OutboundDeliveryItem` → `BillingDocumentItem` (`BILLED_BY`) via `billing_document_items.referenceSdDocument(+Item)`
- `BillingDocument` → `AccountingDocument` (`POSTED_AS`) via header `accountingDocument` + `companyCode` + `fiscalYear`
- `AccountingDocument` → `JournalEntryItemAR` (`HAS_AR_ITEM`)
- `JournalEntryItemAR` → `Payment` (`CLEARED_BY`) via clearing fields

Master data / supporting links:
- `SalesOrderItem` → `Product` (`REFERS_TO_PRODUCT`) via `material`
- `BillingDocumentItem` → `Product` (`BILLS_PRODUCT`) via `material`
- `Customer` → `Address` (`HAS_ADDRESS`) via `business_partner_addresses`
- `Plant` → `Address` (`LOCATED_AT`) via `plants.addressId`
- `Product` → `Plant` (`AVAILABLE_IN_PLANT`) via `product_plants`
- `Product` → `StorageLocation` (`STORED_IN_LOCATION`) via `product_storage_locations`

Cancellation:
- `BillingDocument` → `BillingDocument` (`CANCELS_OR_IS_CANCELLED_BY`) via cancellation fields (direction depends on data semantics)

