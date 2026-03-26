-- Initializes schemas and tables for the SAP O2C dataset.
-- This file is mounted into the Postgres container and executed once on first init.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS graph;

-- ============================================================
-- RAW TABLES
-- Pattern:
--  - payload jsonb stores the original record
--  - key/join columns are STORED generated columns for easy SQL + indexing
-- ============================================================

CREATE TABLE IF NOT EXISTS raw.sales_order_headers (
  row_id bigserial PRIMARY KEY,
  payload jsonb NOT NULL,
  sales_order text GENERATED ALWAYS AS (payload->>'salesOrder') STORED,
  sold_to_party text GENERATED ALWAYS AS (payload->>'soldToParty') STORED,
  -- Keep as text to avoid "generation expression is not immutable" on hosted Postgres.
  creation_date text GENERATED ALWAYS AS (payload->>'creationDate') STORED,
  last_change_datetime text GENERATED ALWAYS AS (payload->>'lastChangeDateTime') STORED,
  total_net_amount text GENERATED ALWAYS AS (payload->>'totalNetAmount') STORED,
  transaction_currency text GENERATED ALWAYS AS (payload->>'transactionCurrency') STORED,
  overall_delivery_status text GENERATED ALWAYS AS (payload->>'overallDeliveryStatus') STORED,
  overall_ord_reltd_billg_status text GENERATED ALWAYS AS (payload->>'overallOrdReltdBillgStatus') STORED
);
CREATE INDEX IF NOT EXISTS idx_soh_sales_order ON raw.sales_order_headers (sales_order);
CREATE INDEX IF NOT EXISTS idx_soh_sold_to_party ON raw.sales_order_headers (sold_to_party);

CREATE TABLE IF NOT EXISTS raw.sales_order_items (
  row_id bigserial PRIMARY KEY,
  payload jsonb NOT NULL,
  sales_order text GENERATED ALWAYS AS (payload->>'salesOrder') STORED,
  sales_order_item text GENERATED ALWAYS AS (payload->>'salesOrderItem') STORED,
  material text GENERATED ALWAYS AS (payload->>'material') STORED,
  material_group text GENERATED ALWAYS AS (payload->>'materialGroup') STORED,
  requested_quantity text GENERATED ALWAYS AS (payload->>'requestedQuantity') STORED,
  requested_quantity_unit text GENERATED ALWAYS AS (payload->>'requestedQuantityUnit') STORED,
  net_amount text GENERATED ALWAYS AS (payload->>'netAmount') STORED,
  transaction_currency text GENERATED ALWAYS AS (payload->>'transactionCurrency') STORED,
  production_plant text GENERATED ALWAYS AS (payload->>'productionPlant') STORED,
  storage_location text GENERATED ALWAYS AS (payload->>'storageLocation') STORED
);
CREATE INDEX IF NOT EXISTS idx_soi_sales_order ON raw.sales_order_items (sales_order);
CREATE INDEX IF NOT EXISTS idx_soi_material ON raw.sales_order_items (material);

CREATE TABLE IF NOT EXISTS raw.sales_order_schedule_lines (
  row_id bigserial PRIMARY KEY,
  payload jsonb NOT NULL,
  sales_order text GENERATED ALWAYS AS (payload->>'salesOrder') STORED,
  sales_order_item text GENERATED ALWAYS AS (payload->>'salesOrderItem') STORED,
  schedule_line text GENERATED ALWAYS AS (payload->>'scheduleLine') STORED,
  confirmed_delivery_date text GENERATED ALWAYS AS (payload->>'confirmedDeliveryDate') STORED,
  confd_order_qty_by_matl_avail_check text GENERATED ALWAYS AS (payload->>'confdOrderQtyByMatlAvailCheck') STORED,
  order_quantity_unit text GENERATED ALWAYS AS (payload->>'orderQuantityUnit') STORED
);
CREATE INDEX IF NOT EXISTS idx_sosl_sales_order ON raw.sales_order_schedule_lines (sales_order);

CREATE TABLE IF NOT EXISTS raw.outbound_delivery_headers (
  row_id bigserial PRIMARY KEY,
  payload jsonb NOT NULL,
  delivery_document text GENERATED ALWAYS AS (payload->>'deliveryDocument') STORED,
  creation_date text GENERATED ALWAYS AS (payload->>'creationDate') STORED,
  shipping_point text GENERATED ALWAYS AS (payload->>'shippingPoint') STORED,
  overall_goods_movement_status text GENERATED ALWAYS AS (payload->>'overallGoodsMovementStatus') STORED,
  overall_picking_status text GENERATED ALWAYS AS (payload->>'overallPickingStatus') STORED
);
CREATE INDEX IF NOT EXISTS idx_odh_delivery_document ON raw.outbound_delivery_headers (delivery_document);

CREATE TABLE IF NOT EXISTS raw.outbound_delivery_items (
  row_id bigserial PRIMARY KEY,
  payload jsonb NOT NULL,
  delivery_document text GENERATED ALWAYS AS (payload->>'deliveryDocument') STORED,
  delivery_document_item text GENERATED ALWAYS AS (payload->>'deliveryDocumentItem') STORED,
  plant text GENERATED ALWAYS AS (payload->>'plant') STORED,
  storage_location text GENERATED ALWAYS AS (payload->>'storageLocation') STORED,
  actual_delivery_quantity text GENERATED ALWAYS AS (payload->>'actualDeliveryQuantity') STORED,
  delivery_quantity_unit text GENERATED ALWAYS AS (payload->>'deliveryQuantityUnit') STORED,
  reference_sd_document text GENERATED ALWAYS AS (payload->>'referenceSdDocument') STORED,
  reference_sd_document_item text GENERATED ALWAYS AS (payload->>'referenceSdDocumentItem') STORED
);
CREATE INDEX IF NOT EXISTS idx_odi_delivery_document ON raw.outbound_delivery_items (delivery_document);
CREATE INDEX IF NOT EXISTS idx_odi_reference_sd_document ON raw.outbound_delivery_items (reference_sd_document);

CREATE TABLE IF NOT EXISTS raw.billing_document_headers (
  row_id bigserial PRIMARY KEY,
  payload jsonb NOT NULL,
  billing_document text GENERATED ALWAYS AS (payload->>'billingDocument') STORED,
  billing_document_type text GENERATED ALWAYS AS (payload->>'billingDocumentType') STORED,
  billing_document_date text GENERATED ALWAYS AS (payload->>'billingDocumentDate') STORED,
  billing_document_is_cancelled text GENERATED ALWAYS AS (payload->>'billingDocumentIsCancelled') STORED,
  cancelled_billing_document text GENERATED ALWAYS AS (payload->>'cancelledBillingDocument') STORED,
  total_net_amount text GENERATED ALWAYS AS (payload->>'totalNetAmount') STORED,
  transaction_currency text GENERATED ALWAYS AS (payload->>'transactionCurrency') STORED,
  company_code text GENERATED ALWAYS AS (payload->>'companyCode') STORED,
  fiscal_year text GENERATED ALWAYS AS (payload->>'fiscalYear') STORED,
  accounting_document text GENERATED ALWAYS AS (payload->>'accountingDocument') STORED,
  sold_to_party text GENERATED ALWAYS AS (payload->>'soldToParty') STORED
);
CREATE INDEX IF NOT EXISTS idx_bh_billing_document ON raw.billing_document_headers (billing_document);
CREATE INDEX IF NOT EXISTS idx_bh_accounting_document ON raw.billing_document_headers (company_code, fiscal_year, accounting_document);

CREATE TABLE IF NOT EXISTS raw.billing_document_items (
  row_id bigserial PRIMARY KEY,
  payload jsonb NOT NULL,
  billing_document text GENERATED ALWAYS AS (payload->>'billingDocument') STORED,
  billing_document_item text GENERATED ALWAYS AS (payload->>'billingDocumentItem') STORED,
  material text GENERATED ALWAYS AS (payload->>'material') STORED,
  billing_quantity text GENERATED ALWAYS AS (payload->>'billingQuantity') STORED,
  billing_quantity_unit text GENERATED ALWAYS AS (payload->>'billingQuantityUnit') STORED,
  net_amount text GENERATED ALWAYS AS (payload->>'netAmount') STORED,
  transaction_currency text GENERATED ALWAYS AS (payload->>'transactionCurrency') STORED,
  reference_sd_document text GENERATED ALWAYS AS (payload->>'referenceSdDocument') STORED,
  reference_sd_document_item text GENERATED ALWAYS AS (payload->>'referenceSdDocumentItem') STORED
);
CREATE INDEX IF NOT EXISTS idx_bdi_billing_document ON raw.billing_document_items (billing_document);
CREATE INDEX IF NOT EXISTS idx_bdi_reference_sd_document ON raw.billing_document_items (reference_sd_document);
CREATE INDEX IF NOT EXISTS idx_bdi_material ON raw.billing_document_items (material);

CREATE TABLE IF NOT EXISTS raw.billing_document_cancellations (
  row_id bigserial PRIMARY KEY,
  payload jsonb NOT NULL,
  billing_document text GENERATED ALWAYS AS (payload->>'billingDocument') STORED,
  billing_document_is_cancelled text GENERATED ALWAYS AS (payload->>'billingDocumentIsCancelled') STORED,
  cancelled_billing_document text GENERATED ALWAYS AS (payload->>'cancelledBillingDocument') STORED
);
CREATE INDEX IF NOT EXISTS idx_bdc_billing_document ON raw.billing_document_cancellations (billing_document);

CREATE TABLE IF NOT EXISTS raw.journal_entry_items_accounts_receivable (
  row_id bigserial PRIMARY KEY,
  payload jsonb NOT NULL,
  company_code text GENERATED ALWAYS AS (payload->>'companyCode') STORED,
  fiscal_year text GENERATED ALWAYS AS (payload->>'fiscalYear') STORED,
  accounting_document text GENERATED ALWAYS AS (payload->>'accountingDocument') STORED,
  accounting_document_item text GENERATED ALWAYS AS (payload->>'accountingDocumentItem') STORED,
  accounting_document_type text GENERATED ALWAYS AS (payload->>'accountingDocumentType') STORED,
  gl_account text GENERATED ALWAYS AS (payload->>'glAccount') STORED,
  reference_document text GENERATED ALWAYS AS (payload->>'referenceDocument') STORED,
  customer text GENERATED ALWAYS AS (payload->>'customer') STORED,
  transaction_currency text GENERATED ALWAYS AS (payload->>'transactionCurrency') STORED,
  amount_in_transaction_currency text GENERATED ALWAYS AS (payload->>'amountInTransactionCurrency') STORED,
  posting_date text GENERATED ALWAYS AS (payload->>'postingDate') STORED,
  document_date text GENERATED ALWAYS AS (payload->>'documentDate') STORED,
  clearing_date text GENERATED ALWAYS AS (payload->>'clearingDate') STORED,
  clearing_accounting_document text GENERATED ALWAYS AS (payload->>'clearingAccountingDocument') STORED,
  clearing_doc_fiscal_year text GENERATED ALWAYS AS (payload->>'clearingDocFiscalYear') STORED
);
CREATE INDEX IF NOT EXISTS idx_jei_ref_doc ON raw.journal_entry_items_accounts_receivable (reference_document);
CREATE INDEX IF NOT EXISTS idx_jei_acc_doc ON raw.journal_entry_items_accounts_receivable (company_code, fiscal_year, accounting_document);

CREATE TABLE IF NOT EXISTS raw.payments_accounts_receivable (
  row_id bigserial PRIMARY KEY,
  payload jsonb NOT NULL,
  company_code text GENERATED ALWAYS AS (payload->>'companyCode') STORED,
  fiscal_year text GENERATED ALWAYS AS (payload->>'fiscalYear') STORED,
  accounting_document text GENERATED ALWAYS AS (payload->>'accountingDocument') STORED,
  accounting_document_item text GENERATED ALWAYS AS (payload->>'accountingDocumentItem') STORED,
  customer text GENERATED ALWAYS AS (payload->>'customer') STORED,
  transaction_currency text GENERATED ALWAYS AS (payload->>'transactionCurrency') STORED,
  amount_in_transaction_currency text GENERATED ALWAYS AS (payload->>'amountInTransactionCurrency') STORED,
  clearing_date text GENERATED ALWAYS AS (payload->>'clearingDate') STORED,
  clearing_accounting_document text GENERATED ALWAYS AS (payload->>'clearingAccountingDocument') STORED,
  clearing_doc_fiscal_year text GENERATED ALWAYS AS (payload->>'clearingDocFiscalYear') STORED,
  invoice_reference text GENERATED ALWAYS AS (payload->>'invoiceReference') STORED,
  invoice_reference_fiscal_year text GENERATED ALWAYS AS (payload->>'invoiceReferenceFiscalYear') STORED
);
CREATE INDEX IF NOT EXISTS idx_pay_customer ON raw.payments_accounts_receivable (customer);
CREATE INDEX IF NOT EXISTS idx_pay_clearing_doc ON raw.payments_accounts_receivable (company_code, clearing_doc_fiscal_year, clearing_accounting_document);

CREATE TABLE IF NOT EXISTS raw.business_partners (
  row_id bigserial PRIMARY KEY,
  payload jsonb NOT NULL,
  business_partner text GENERATED ALWAYS AS (payload->>'businessPartner') STORED,
  customer text GENERATED ALWAYS AS (payload->>'customer') STORED,
  business_partner_category text GENERATED ALWAYS AS (payload->>'businessPartnerCategory') STORED,
  business_partner_name text GENERATED ALWAYS AS (payload->>'businessPartnerName') STORED,
  business_partner_full_name text GENERATED ALWAYS AS (payload->>'businessPartnerFullName') STORED,
  business_partner_grouping text GENERATED ALWAYS AS (payload->>'businessPartnerGrouping') STORED,
  business_partner_is_blocked text GENERATED ALWAYS AS (payload->>'businessPartnerIsBlocked') STORED,
  is_marked_for_archiving text GENERATED ALWAYS AS (payload->>'isMarkedForArchiving') STORED
);
CREATE INDEX IF NOT EXISTS idx_bp_business_partner ON raw.business_partners (business_partner);

CREATE TABLE IF NOT EXISTS raw.business_partner_addresses (
  row_id bigserial PRIMARY KEY,
  payload jsonb NOT NULL,
  business_partner text GENERATED ALWAYS AS (payload->>'businessPartner') STORED,
  address_id text GENERATED ALWAYS AS (payload->>'addressId') STORED,
  address_uuid text GENERATED ALWAYS AS (payload->>'addressUuid') STORED,
  validity_start_date text GENERATED ALWAYS AS (payload->>'validityStartDate') STORED,
  validity_end_date text GENERATED ALWAYS AS (payload->>'validityEndDate') STORED,
  street_name text GENERATED ALWAYS AS (payload->>'streetName') STORED,
  city_name text GENERATED ALWAYS AS (payload->>'cityName') STORED,
  region text GENERATED ALWAYS AS (payload->>'region') STORED,
  country text GENERATED ALWAYS AS (payload->>'country') STORED,
  postal_code text GENERATED ALWAYS AS (payload->>'postalCode') STORED
);
CREATE INDEX IF NOT EXISTS idx_bpa_business_partner ON raw.business_partner_addresses (business_partner);
CREATE INDEX IF NOT EXISTS idx_bpa_address_id ON raw.business_partner_addresses (address_id);

CREATE TABLE IF NOT EXISTS raw.customer_company_assignments (
  row_id bigserial PRIMARY KEY,
  payload jsonb NOT NULL,
  customer text GENERATED ALWAYS AS (payload->>'customer') STORED,
  company_code text GENERATED ALWAYS AS (payload->>'companyCode') STORED,
  reconciliation_account text GENERATED ALWAYS AS (payload->>'reconciliationAccount') STORED,
  deletion_indicator text GENERATED ALWAYS AS (payload->>'deletionIndicator') STORED,
  customer_account_group text GENERATED ALWAYS AS (payload->>'customerAccountGroup') STORED
);
CREATE INDEX IF NOT EXISTS idx_cca_customer ON raw.customer_company_assignments (customer);

CREATE TABLE IF NOT EXISTS raw.customer_sales_area_assignments (
  row_id bigserial PRIMARY KEY,
  payload jsonb NOT NULL,
  customer text GENERATED ALWAYS AS (payload->>'customer') STORED,
  sales_organization text GENERATED ALWAYS AS (payload->>'salesOrganization') STORED,
  distribution_channel text GENERATED ALWAYS AS (payload->>'distributionChannel') STORED,
  division text GENERATED ALWAYS AS (payload->>'division') STORED,
  currency text GENERATED ALWAYS AS (payload->>'currency') STORED,
  customer_payment_terms text GENERATED ALWAYS AS (payload->>'customerPaymentTerms') STORED,
  incoterms_classification text GENERATED ALWAYS AS (payload->>'incotermsClassification') STORED,
  incoterms_location1 text GENERATED ALWAYS AS (payload->>'incotermsLocation1') STORED
);
CREATE INDEX IF NOT EXISTS idx_csa_customer ON raw.customer_sales_area_assignments (customer);

CREATE TABLE IF NOT EXISTS raw.products (
  row_id bigserial PRIMARY KEY,
  payload jsonb NOT NULL,
  product text GENERATED ALWAYS AS (payload->>'product') STORED,
  product_type text GENERATED ALWAYS AS (payload->>'productType') STORED,
  product_group text GENERATED ALWAYS AS (payload->>'productGroup') STORED,
  base_unit text GENERATED ALWAYS AS (payload->>'baseUnit') STORED,
  division text GENERATED ALWAYS AS (payload->>'division') STORED,
  is_marked_for_deletion text GENERATED ALWAYS AS (payload->>'isMarkedForDeletion') STORED,
  gross_weight text GENERATED ALWAYS AS (payload->>'grossWeight') STORED,
  net_weight text GENERATED ALWAYS AS (payload->>'netWeight') STORED,
  weight_unit text GENERATED ALWAYS AS (payload->>'weightUnit') STORED
);
CREATE INDEX IF NOT EXISTS idx_products_product ON raw.products (product);

CREATE TABLE IF NOT EXISTS raw.product_descriptions (
  row_id bigserial PRIMARY KEY,
  payload jsonb NOT NULL,
  product text GENERATED ALWAYS AS (payload->>'product') STORED,
  language text GENERATED ALWAYS AS (payload->>'language') STORED,
  product_description text GENERATED ALWAYS AS (payload->>'productDescription') STORED
);
CREATE INDEX IF NOT EXISTS idx_prod_desc_product ON raw.product_descriptions (product);

CREATE TABLE IF NOT EXISTS raw.plants (
  row_id bigserial PRIMARY KEY,
  payload jsonb NOT NULL,
  plant text GENERATED ALWAYS AS (payload->>'plant') STORED,
  plant_name text GENERATED ALWAYS AS (payload->>'plantName') STORED,
  address_id text GENERATED ALWAYS AS (payload->>'addressId') STORED,
  sales_organization text GENERATED ALWAYS AS (payload->>'salesOrganization') STORED,
  distribution_channel text GENERATED ALWAYS AS (payload->>'distributionChannel') STORED,
  division text GENERATED ALWAYS AS (payload->>'division') STORED,
  is_marked_for_archiving text GENERATED ALWAYS AS (payload->>'isMarkedForArchiving') STORED
);
CREATE INDEX IF NOT EXISTS idx_plants_plant ON raw.plants (plant);

CREATE TABLE IF NOT EXISTS raw.product_plants (
  row_id bigserial PRIMARY KEY,
  payload jsonb NOT NULL,
  product text GENERATED ALWAYS AS (payload->>'product') STORED,
  plant text GENERATED ALWAYS AS (payload->>'plant') STORED,
  availability_check_type text GENERATED ALWAYS AS (payload->>'availabilityCheckType') STORED,
  profit_center text GENERATED ALWAYS AS (payload->>'profitCenter') STORED,
  mrp_type text GENERATED ALWAYS AS (payload->>'mrpType') STORED
);
CREATE INDEX IF NOT EXISTS idx_product_plants_product ON raw.product_plants (product);
CREATE INDEX IF NOT EXISTS idx_product_plants_plant ON raw.product_plants (plant);

CREATE TABLE IF NOT EXISTS raw.product_storage_locations (
  row_id bigserial PRIMARY KEY,
  payload jsonb NOT NULL,
  product text GENERATED ALWAYS AS (payload->>'product') STORED,
  plant text GENERATED ALWAYS AS (payload->>'plant') STORED,
  storage_location text GENERATED ALWAYS AS (payload->>'storageLocation') STORED,
  physical_inventory_block_ind text GENERATED ALWAYS AS (payload->>'physicalInventoryBlockInd') STORED,
  date_of_last_posted_cnt_un_rstrcd_stk text GENERATED ALWAYS AS (payload->>'dateOfLastPostedCntUnRstrcdStk') STORED
);
CREATE INDEX IF NOT EXISTS idx_psl_product ON raw.product_storage_locations (product);

-- ============================================================
-- GRAPH TABLES (projection; populated by a separate script)
-- ============================================================

CREATE TABLE IF NOT EXISTS graph.graph_nodes (
  node_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  node_key text NOT NULL UNIQUE,
  node_type text NOT NULL,
  raw_table text,
  raw_pk jsonb,
  label text NOT NULL,
  attrs jsonb NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS idx_graph_nodes_type ON graph.graph_nodes (node_type);

CREATE TABLE IF NOT EXISTS graph.graph_edges (
  edge_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  edge_key text NOT NULL UNIQUE,
  src_node_id uuid NOT NULL REFERENCES graph.graph_nodes(node_id) ON DELETE CASCADE,
  dst_node_id uuid NOT NULL REFERENCES graph.graph_nodes(node_id) ON DELETE CASCADE,
  edge_type text NOT NULL,
  evidence jsonb,
  UNIQUE (src_node_id, edge_type, dst_node_id)
);
CREATE INDEX IF NOT EXISTS idx_graph_edges_src_type ON graph.graph_edges (src_node_id, edge_type);
CREATE INDEX IF NOT EXISTS idx_graph_edges_dst_type ON graph.graph_edges (dst_node_id, edge_type);
CREATE INDEX IF NOT EXISTS idx_graph_edges_type ON graph.graph_edges (edge_type);

