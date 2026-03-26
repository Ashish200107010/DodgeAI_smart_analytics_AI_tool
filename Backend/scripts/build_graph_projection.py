from __future__ import annotations

import argparse
import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv


def load_env() -> None:
    backend_dir = Path(__file__).resolve().parents[1]
    env_path = backend_dir / ".env"
    if env_path.exists():
        load_dotenv(env_path)
    else:
        load_dotenv()


def to_psycopg_dsn(database_url: str) -> str:
    if database_url.startswith("postgresql+psycopg://"):
        return "postgresql://" + database_url.removeprefix("postgresql+psycopg://")
    if database_url.startswith("postgresql://") or database_url.startswith("postgres://"):
        return database_url.replace("postgres://", "postgresql://")
    return database_url


def run_init_db_if_missing(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute("SELECT to_regclass('graph.graph_nodes') AS t;")
        exists = cur.fetchone()[0]  # type: ignore[index]
        if exists is not None:
            return

        init_path = Path(__file__).resolve().parent / "init_db.sql"
        if not init_path.exists():
            raise SystemExit(f"init_db.sql not found at {init_path}")

        print("[init] graph/raw schemas missing. Running init_db.sql ...")
        sql_text = init_path.read_text(encoding="utf-8")
        # Simple splitter (no stored procedures expected)
        statements: list[str] = []
        for line in sql_text.splitlines():
            if line.lstrip().startswith("--"):
                continue
            statements.append(line)
        cleaned = "\n".join(statements)
        for stmt in cleaned.split(";"):
            stmt = stmt.strip()
            if stmt:
                cur.execute(stmt)
        conn.commit()


def main() -> None:
    load_env()

    parser = argparse.ArgumentParser(description="Build graph projection tables from raw.* dataset tables.")
    parser.add_argument(
        "--truncate",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Truncate graph tables before rebuild (default: true).",
    )
    args = parser.parse_args()

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL is not set. Create Backend/.env or set env var DATABASE_URL.")

    dsn = to_psycopg_dsn(database_url)

    with psycopg.connect(dsn) as conn:
        conn.execute("SET statement_timeout TO '0'")
        run_init_db_if_missing(conn)

        with conn.cursor() as cur:
            if args.truncate:
                print("[graph] truncating graph.graph_edges and graph.graph_nodes ...")
                cur.execute("TRUNCATE TABLE graph.graph_edges, graph.graph_nodes CASCADE;")
                conn.commit()

            # --------------------------
            # NODES
            # --------------------------
            print("[graph] inserting nodes ...")

            cur.execute(
                """
                INSERT INTO graph.graph_nodes (node_key, node_type, label, attrs)
                SELECT DISTINCT
                  'SalesOrder:' || soh.sales_order AS node_key,
                  'SalesOrder' AS node_type,
                  'SO ' || soh.sales_order AS label,
                  jsonb_build_object(
                    'salesOrder', soh.sales_order,
                    'soldToParty', soh.sold_to_party,
                    'creationDate', soh.creation_date,
                    'totalNetAmount', soh.total_net_amount,
                    'transactionCurrency', soh.transaction_currency,
                    'overallDeliveryStatus', soh.overall_delivery_status,
                    'overallBillingStatus', soh.overall_ord_reltd_billg_status
                  ) AS attrs
                FROM raw.sales_order_headers soh
                WHERE soh.sales_order IS NOT NULL AND soh.sales_order <> ''
                ON CONFLICT (node_key) DO NOTHING;
                """
            )

            cur.execute(
                """
                INSERT INTO graph.graph_nodes (node_key, node_type, label, attrs)
                SELECT DISTINCT
                  'SalesOrderItem:' || soi.sales_order || '|' || soi.sales_order_item AS node_key,
                  'SalesOrderItem' AS node_type,
                  'SO Item ' || soi.sales_order || '/' || soi.sales_order_item AS label,
                  jsonb_build_object(
                    'salesOrder', soi.sales_order,
                    'salesOrderItem', soi.sales_order_item,
                    'material', soi.material,
                    'requestedQuantity', soi.requested_quantity,
                    'requestedQuantityUnit', soi.requested_quantity_unit,
                    'netAmount', soi.net_amount,
                    'transactionCurrency', soi.transaction_currency,
                    'productionPlant', soi.production_plant,
                    'storageLocation', soi.storage_location
                  ) AS attrs
                FROM raw.sales_order_items soi
                WHERE soi.sales_order IS NOT NULL AND soi.sales_order <> ''
                  AND soi.sales_order_item IS NOT NULL AND soi.sales_order_item <> ''
                ON CONFLICT (node_key) DO NOTHING;
                """
            )

            cur.execute(
                """
                INSERT INTO graph.graph_nodes (node_key, node_type, label, attrs)
                SELECT DISTINCT
                  'OutboundDelivery:' || odh.delivery_document AS node_key,
                  'OutboundDelivery' AS node_type,
                  'Delivery ' || odh.delivery_document AS label,
                  jsonb_build_object(
                    'deliveryDocument', odh.delivery_document,
                    'creationDate', odh.creation_date,
                    'shippingPoint', odh.shipping_point,
                    'overallGoodsMovementStatus', odh.overall_goods_movement_status,
                    'overallPickingStatus', odh.overall_picking_status
                  ) AS attrs
                FROM raw.outbound_delivery_headers odh
                WHERE odh.delivery_document IS NOT NULL AND odh.delivery_document <> ''
                ON CONFLICT (node_key) DO NOTHING;
                """
            )

            # Ensure any delivery appearing only in items is also present as a node.
            cur.execute(
                """
                INSERT INTO graph.graph_nodes (node_key, node_type, label, attrs)
                SELECT DISTINCT
                  'OutboundDelivery:' || odi.delivery_document AS node_key,
                  'OutboundDelivery' AS node_type,
                  'Delivery ' || odi.delivery_document AS label,
                  jsonb_build_object('deliveryDocument', odi.delivery_document) AS attrs
                FROM raw.outbound_delivery_items odi
                WHERE odi.delivery_document IS NOT NULL AND odi.delivery_document <> ''
                ON CONFLICT (node_key) DO NOTHING;
                """
            )

            cur.execute(
                """
                INSERT INTO graph.graph_nodes (node_key, node_type, label, attrs)
                SELECT DISTINCT
                  'OutboundDeliveryItem:' || odi.delivery_document || '|' || odi.delivery_document_item AS node_key,
                  'OutboundDeliveryItem' AS node_type,
                  'Delivery Item ' || odi.delivery_document || '/' || odi.delivery_document_item AS label,
                  jsonb_build_object(
                    'deliveryDocument', odi.delivery_document,
                    'deliveryDocumentItem', odi.delivery_document_item,
                    'referenceSalesOrder', odi.reference_sd_document,
                    'referenceSalesOrderItem', odi.reference_sd_document_item,
                    'plant', odi.plant,
                    'storageLocation', odi.storage_location,
                    'actualDeliveryQuantity', odi.actual_delivery_quantity,
                    'deliveryQuantityUnit', odi.delivery_quantity_unit
                  ) AS attrs
                FROM raw.outbound_delivery_items odi
                WHERE odi.delivery_document IS NOT NULL AND odi.delivery_document <> ''
                  AND odi.delivery_document_item IS NOT NULL AND odi.delivery_document_item <> ''
                ON CONFLICT (node_key) DO NOTHING;
                """
            )

            cur.execute(
                """
                INSERT INTO graph.graph_nodes (node_key, node_type, label, attrs)
                SELECT DISTINCT
                  'BillingDocument:' || bh.billing_document AS node_key,
                  'BillingDocument' AS node_type,
                  'Billing ' || bh.billing_document AS label,
                  jsonb_build_object(
                    'billingDocument', bh.billing_document,
                    'billingDocumentType', bh.billing_document_type,
                    'billingDocumentDate', bh.billing_document_date,
                    'totalNetAmount', bh.total_net_amount,
                    'transactionCurrency', bh.transaction_currency,
                    'companyCode', bh.company_code,
                    'fiscalYear', bh.fiscal_year,
                    'accountingDocument', bh.accounting_document,
                    'soldToParty', bh.sold_to_party,
                    'isCancelled', bh.billing_document_is_cancelled,
                    'cancelledBillingDocument', bh.cancelled_billing_document
                  ) AS attrs
                FROM raw.billing_document_headers bh
                WHERE bh.billing_document IS NOT NULL AND bh.billing_document <> ''
                ON CONFLICT (node_key) DO NOTHING;
                """
            )

            cur.execute(
                """
                INSERT INTO graph.graph_nodes (node_key, node_type, label, attrs)
                SELECT DISTINCT
                  'BillingDocumentItem:' || bdi.billing_document || '|' || bdi.billing_document_item AS node_key,
                  'BillingDocumentItem' AS node_type,
                  'Billing Item ' || bdi.billing_document || '/' || bdi.billing_document_item AS label,
                  jsonb_build_object(
                    'billingDocument', bdi.billing_document,
                    'billingDocumentItem', bdi.billing_document_item,
                    'material', bdi.material,
                    'billingQuantity', bdi.billing_quantity,
                    'billingQuantityUnit', bdi.billing_quantity_unit,
                    'netAmount', bdi.net_amount,
                    'transactionCurrency', bdi.transaction_currency,
                    'referenceDelivery', bdi.reference_sd_document,
                    'referenceDeliveryItem', bdi.reference_sd_document_item
                  ) AS attrs
                FROM raw.billing_document_items bdi
                WHERE bdi.billing_document IS NOT NULL AND bdi.billing_document <> ''
                  AND bdi.billing_document_item IS NOT NULL AND bdi.billing_document_item <> ''
                ON CONFLICT (node_key) DO NOTHING;
                """
            )

            cur.execute(
                """
                INSERT INTO graph.graph_nodes (node_key, node_type, label, attrs)
                SELECT DISTINCT
                  'JournalEntryItemAR:' || je.company_code || '|' || je.fiscal_year || '|' || je.accounting_document || '|' || je.accounting_document_item AS node_key,
                  'JournalEntryItemAR' AS node_type,
                  'Journal ' || je.accounting_document || ' (Item ' || je.accounting_document_item || ')' AS label,
                  jsonb_build_object(
                    'companyCode', je.company_code,
                    'fiscalYear', je.fiscal_year,
                    'accountingDocument', je.accounting_document,
                    'accountingDocumentItem', je.accounting_document_item,
                    'accountingDocumentType', je.accounting_document_type,
                    'glAccount', je.gl_account,
                    'referenceDocument', je.reference_document,
                    'customer', je.customer,
                    'transactionCurrency', je.transaction_currency,
                    'amountInTransactionCurrency', je.amount_in_transaction_currency,
                    'postingDate', je.posting_date,
                    'documentDate', je.document_date,
                    'clearingDate', je.clearing_date,
                    'clearingAccountingDocument', je.clearing_accounting_document,
                    'clearingDocFiscalYear', je.clearing_doc_fiscal_year
                  ) AS attrs
                FROM raw.journal_entry_items_accounts_receivable je
                WHERE je.company_code IS NOT NULL AND je.company_code <> ''
                  AND je.fiscal_year IS NOT NULL AND je.fiscal_year <> ''
                  AND je.accounting_document IS NOT NULL AND je.accounting_document <> ''
                  AND je.accounting_document_item IS NOT NULL AND je.accounting_document_item <> ''
                ON CONFLICT (node_key) DO NOTHING;
                """
            )

            # Products: from master table + any material referenced in items
            cur.execute(
                """
                INSERT INTO graph.graph_nodes (node_key, node_type, label, attrs)
                SELECT DISTINCT
                  'Product:' || p.product AS node_key,
                  'Product' AS node_type,
                  COALESCE(pd.product_description, 'Product ' || p.product) AS label,
                  jsonb_build_object(
                    'product', p.product,
                    'productType', p.product_type,
                    'productGroup', p.product_group,
                    'baseUnit', p.base_unit,
                    'division', p.division
                  ) AS attrs
                FROM raw.products p
                LEFT JOIN raw.product_descriptions pd
                  ON pd.product = p.product AND pd.language = 'EN'
                WHERE p.product IS NOT NULL AND p.product <> ''
                ON CONFLICT (node_key) DO NOTHING;
                """
            )

            # Ensure any material referenced by items exists as a Product node even if missing in raw.products
            cur.execute(
                """
                INSERT INTO graph.graph_nodes (node_key, node_type, label, attrs)
                SELECT DISTINCT
                  'Product:' || m.material AS node_key,
                  'Product' AS node_type,
                  COALESCE(pd.product_description, 'Product ' || m.material) AS label,
                  jsonb_build_object('product', m.material) AS attrs
                FROM (
                  SELECT DISTINCT material FROM raw.sales_order_items WHERE material IS NOT NULL AND material <> ''
                  UNION
                  SELECT DISTINCT material FROM raw.billing_document_items WHERE material IS NOT NULL AND material <> ''
                ) m
                LEFT JOIN raw.product_descriptions pd
                  ON pd.product = m.material AND pd.language = 'EN'
                ON CONFLICT (node_key) DO NOTHING;
                """
            )

            # Payment nodes: union clearing docs from payments + journal entries.
            cur.execute(
                """
                WITH clearing_docs AS (
                  SELECT DISTINCT
                    company_code,
                    clearing_doc_fiscal_year AS fiscal_year,
                    clearing_accounting_document AS clearing_doc,
                    clearing_date
                  FROM raw.journal_entry_items_accounts_receivable
                  WHERE company_code IS NOT NULL AND company_code <> ''
                    AND clearing_doc_fiscal_year IS NOT NULL AND clearing_doc_fiscal_year <> ''
                    AND clearing_accounting_document IS NOT NULL AND clearing_accounting_document <> ''
                  UNION
                  SELECT DISTINCT
                    company_code,
                    clearing_doc_fiscal_year AS fiscal_year,
                    clearing_accounting_document AS clearing_doc,
                    clearing_date
                  FROM raw.payments_accounts_receivable
                  WHERE company_code IS NOT NULL AND company_code <> ''
                    AND clearing_doc_fiscal_year IS NOT NULL AND clearing_doc_fiscal_year <> ''
                    AND clearing_accounting_document IS NOT NULL AND clearing_accounting_document <> ''
                )
                INSERT INTO graph.graph_nodes (node_key, node_type, label, attrs)
                SELECT DISTINCT
                  'Payment:' || company_code || '|' || fiscal_year || '|' || clearing_doc AS node_key,
                  'Payment' AS node_type,
                  'Payment ' || clearing_doc AS label,
                  jsonb_build_object(
                    'companyCode', company_code,
                    'fiscalYear', fiscal_year,
                    'clearingAccountingDocument', clearing_doc,
                    'clearingDate', clearing_date
                  ) AS attrs
                FROM clearing_docs
                ON CONFLICT (node_key) DO NOTHING;
                """
            )

            conn.commit()

            # --------------------------
            # EDGES
            # --------------------------
            print("[graph] inserting edges ...")

            # SalesOrder -> SalesOrderItem (granular)
            cur.execute(
                """
                INSERT INTO graph.graph_edges (edge_key, src_node_id, dst_node_id, edge_type, evidence)
                SELECT DISTINCT
                  'HAS_ITEM:' || so.node_key || '->' || soi.node_key AS edge_key,
                  so.node_id AS src_node_id,
                  soi.node_id AS dst_node_id,
                  'HAS_ITEM' AS edge_type,
                  jsonb_build_object('salesOrder', soi.attrs->>'salesOrder', 'salesOrderItem', soi.attrs->>'salesOrderItem') AS evidence
                FROM graph.graph_nodes so
                JOIN graph.graph_nodes soi
                  ON soi.node_type = 'SalesOrderItem'
                 AND soi.node_key LIKE ('SalesOrderItem:' || substring(so.node_key from 12) || '|%')
                WHERE so.node_type = 'SalesOrder'
                ON CONFLICT DO NOTHING;
                """
            )

            # SalesOrder -> OutboundDelivery (non-granular)
            cur.execute(
                """
                INSERT INTO graph.graph_edges (edge_key, src_node_id, dst_node_id, edge_type, evidence)
                SELECT DISTINCT
                  'DELIVERED_AS:' || so.node_key || '->' || d.node_key AS edge_key,
                  so.node_id,
                  d.node_id,
                  'DELIVERED_AS' AS edge_type,
                  jsonb_build_object('salesOrder', odi.reference_sd_document, 'deliveryDocument', odi.delivery_document) AS evidence
                FROM raw.outbound_delivery_items odi
                JOIN graph.graph_nodes so ON so.node_key = 'SalesOrder:' || odi.reference_sd_document
                JOIN graph.graph_nodes d  ON d.node_key  = 'OutboundDelivery:' || odi.delivery_document
                WHERE odi.reference_sd_document IS NOT NULL AND odi.reference_sd_document <> ''
                  AND odi.delivery_document IS NOT NULL AND odi.delivery_document <> ''
                ON CONFLICT DO NOTHING;
                """
            )

            # OutboundDelivery -> OutboundDeliveryItem (granular)
            cur.execute(
                """
                INSERT INTO graph.graph_edges (edge_key, src_node_id, dst_node_id, edge_type, evidence)
                SELECT DISTINCT
                  'HAS_ITEM:' || d.node_key || '->' || di.node_key AS edge_key,
                  d.node_id,
                  di.node_id,
                  'HAS_ITEM' AS edge_type,
                  jsonb_build_object('deliveryDocument', odi.delivery_document, 'deliveryDocumentItem', odi.delivery_document_item) AS evidence
                FROM raw.outbound_delivery_items odi
                JOIN graph.graph_nodes d  ON d.node_key = 'OutboundDelivery:' || odi.delivery_document
                JOIN graph.graph_nodes di ON di.node_key = 'OutboundDeliveryItem:' || odi.delivery_document || '|' || odi.delivery_document_item
                WHERE odi.delivery_document IS NOT NULL AND odi.delivery_document <> ''
                ON CONFLICT DO NOTHING;
                """
            )

            # SalesOrderItem -> OutboundDeliveryItem (granular)
            cur.execute(
                """
                INSERT INTO graph.graph_edges (edge_key, src_node_id, dst_node_id, edge_type, evidence)
                SELECT DISTINCT
                  'FULFILLED_BY:' || soi.node_key || '->' || di.node_key AS edge_key,
                  soi.node_id,
                  di.node_id,
                  'FULFILLED_BY' AS edge_type,
                  jsonb_build_object('salesOrder', odi.reference_sd_document, 'salesOrderItem', odi.reference_sd_document_item, 'deliveryDocument', odi.delivery_document) AS evidence
                FROM raw.outbound_delivery_items odi
                JOIN graph.graph_nodes soi
                  ON soi.node_key = 'SalesOrderItem:' || odi.reference_sd_document || '|' || (ltrim(odi.reference_sd_document_item, '0'))
                JOIN graph.graph_nodes di
                  ON di.node_key = 'OutboundDeliveryItem:' || odi.delivery_document || '|' || odi.delivery_document_item
                WHERE odi.reference_sd_document IS NOT NULL AND odi.reference_sd_document <> ''
                  AND odi.reference_sd_document_item IS NOT NULL AND odi.reference_sd_document_item <> ''
                  AND odi.delivery_document IS NOT NULL AND odi.delivery_document <> ''
                ON CONFLICT DO NOTHING;
                """
            )

            # BillingDocument -> BillingDocumentItem (granular)
            cur.execute(
                """
                INSERT INTO graph.graph_edges (edge_key, src_node_id, dst_node_id, edge_type, evidence)
                SELECT DISTINCT
                  'HAS_ITEM:' || b.node_key || '->' || bi.node_key AS edge_key,
                  b.node_id,
                  bi.node_id,
                  'HAS_ITEM' AS edge_type,
                  jsonb_build_object('billingDocument', bdi.billing_document, 'billingDocumentItem', bdi.billing_document_item) AS evidence
                FROM raw.billing_document_items bdi
                JOIN graph.graph_nodes b  ON b.node_key = 'BillingDocument:' || bdi.billing_document
                JOIN graph.graph_nodes bi ON bi.node_key = 'BillingDocumentItem:' || bdi.billing_document || '|' || bdi.billing_document_item
                WHERE bdi.billing_document IS NOT NULL AND bdi.billing_document <> ''
                ON CONFLICT DO NOTHING;
                """
            )

            # OutboundDelivery -> BillingDocument (non-granular)
            cur.execute(
                """
                INSERT INTO graph.graph_edges (edge_key, src_node_id, dst_node_id, edge_type, evidence)
                SELECT DISTINCT
                  'BILLED_AS:' || d.node_key || '->' || b.node_key AS edge_key,
                  d.node_id,
                  b.node_id,
                  'BILLED_AS' AS edge_type,
                  jsonb_build_object('deliveryDocument', bdi.reference_sd_document, 'billingDocument', bdi.billing_document) AS evidence
                FROM raw.billing_document_items bdi
                JOIN graph.graph_nodes d ON d.node_key = 'OutboundDelivery:' || bdi.reference_sd_document
                JOIN graph.graph_nodes b ON b.node_key = 'BillingDocument:' || bdi.billing_document
                WHERE bdi.reference_sd_document IS NOT NULL AND bdi.reference_sd_document <> ''
                  AND bdi.billing_document IS NOT NULL AND bdi.billing_document <> ''
                ON CONFLICT DO NOTHING;
                """
            )

            # OutboundDeliveryItem -> BillingDocumentItem (granular)
            cur.execute(
                """
                INSERT INTO graph.graph_edges (edge_key, src_node_id, dst_node_id, edge_type, evidence)
                SELECT DISTINCT
                  'BILLED_BY:' || di.node_key || '->' || bi.node_key AS edge_key,
                  di.node_id,
                  bi.node_id,
                  'BILLED_BY' AS edge_type,
                  jsonb_build_object('deliveryDocument', bdi.reference_sd_document, 'billingDocument', bdi.billing_document) AS evidence
                FROM raw.billing_document_items bdi
                JOIN graph.graph_nodes di
                  ON di.node_key = 'OutboundDeliveryItem:' || bdi.reference_sd_document || '|' || lpad(bdi.reference_sd_document_item, 6, '0')
                JOIN graph.graph_nodes bi
                  ON bi.node_key = 'BillingDocumentItem:' || bdi.billing_document || '|' || bdi.billing_document_item
                WHERE bdi.reference_sd_document IS NOT NULL AND bdi.reference_sd_document <> ''
                  AND bdi.reference_sd_document_item IS NOT NULL AND bdi.reference_sd_document_item <> ''
                  AND bdi.billing_document IS NOT NULL AND bdi.billing_document <> ''
                ON CONFLICT DO NOTHING;
                """
            )

            # BillingDocument -> JournalEntryItemAR (non-granular)
            cur.execute(
                """
                INSERT INTO graph.graph_edges (edge_key, src_node_id, dst_node_id, edge_type, evidence)
                SELECT DISTINCT
                  'POSTED_AS:' || b.node_key || '->' || je.node_key AS edge_key,
                  b.node_id,
                  je.node_id,
                  'POSTED_AS' AS edge_type,
                  jsonb_build_object('billingDocument', ar.reference_document, 'accountingDocument', ar.accounting_document) AS evidence
                FROM raw.journal_entry_items_accounts_receivable ar
                JOIN graph.graph_nodes b
                  ON b.node_key = 'BillingDocument:' || ar.reference_document
                JOIN graph.graph_nodes je
                  ON je.node_key = 'JournalEntryItemAR:' || ar.company_code || '|' || ar.fiscal_year || '|' || ar.accounting_document || '|' || ar.accounting_document_item
                WHERE ar.reference_document IS NOT NULL AND ar.reference_document <> ''
                ON CONFLICT DO NOTHING;
                """
            )

            # JournalEntryItemAR -> Payment (non-granular)
            cur.execute(
                """
                INSERT INTO graph.graph_edges (edge_key, src_node_id, dst_node_id, edge_type, evidence)
                SELECT DISTINCT
                  'CLEARED_BY:' || je.node_key || '->' || p.node_key AS edge_key,
                  je.node_id,
                  p.node_id,
                  'CLEARED_BY' AS edge_type,
                  jsonb_build_object(
                    'clearingAccountingDocument', ar.clearing_accounting_document,
                    'clearingDocFiscalYear', ar.clearing_doc_fiscal_year,
                    'clearingDate', ar.clearing_date
                  ) AS evidence
                FROM raw.journal_entry_items_accounts_receivable ar
                JOIN graph.graph_nodes je
                  ON je.node_key = 'JournalEntryItemAR:' || ar.company_code || '|' || ar.fiscal_year || '|' || ar.accounting_document || '|' || ar.accounting_document_item
                JOIN graph.graph_nodes p
                  ON p.node_key = 'Payment:' || ar.company_code || '|' || ar.clearing_doc_fiscal_year || '|' || ar.clearing_accounting_document
                WHERE ar.clearing_accounting_document IS NOT NULL AND ar.clearing_accounting_document <> ''
                  AND ar.clearing_doc_fiscal_year IS NOT NULL AND ar.clearing_doc_fiscal_year <> ''
                ON CONFLICT DO NOTHING;
                """
            )

            # Item -> Product (granular)
            cur.execute(
                """
                INSERT INTO graph.graph_edges (edge_key, src_node_id, dst_node_id, edge_type, evidence)
                SELECT DISTINCT
                  'REFERS_TO_PRODUCT:' || soi.node_key || '->' || p.node_key AS edge_key,
                  soi.node_id,
                  p.node_id,
                  'REFERS_TO_PRODUCT' AS edge_type,
                  jsonb_build_object('material', soi.attrs->>'material') AS evidence
                FROM graph.graph_nodes soi
                JOIN graph.graph_nodes p
                  ON p.node_key = 'Product:' || (soi.attrs->>'material')
                WHERE soi.node_type = 'SalesOrderItem'
                  AND (soi.attrs->>'material') IS NOT NULL AND (soi.attrs->>'material') <> ''
                ON CONFLICT DO NOTHING;
                """
            )

            cur.execute(
                """
                INSERT INTO graph.graph_edges (edge_key, src_node_id, dst_node_id, edge_type, evidence)
                SELECT DISTINCT
                  'REFERS_TO_PRODUCT:' || bi.node_key || '->' || p.node_key AS edge_key,
                  bi.node_id,
                  p.node_id,
                  'REFERS_TO_PRODUCT' AS edge_type,
                  jsonb_build_object('material', bi.attrs->>'material') AS evidence
                FROM graph.graph_nodes bi
                JOIN graph.graph_nodes p
                  ON p.node_key = 'Product:' || (bi.attrs->>'material')
                WHERE bi.node_type = 'BillingDocumentItem'
                  AND (bi.attrs->>'material') IS NOT NULL AND (bi.attrs->>'material') <> ''
                ON CONFLICT DO NOTHING;
                """
            )

            conn.commit()

            # Summary counts
            cur.execute("SELECT node_type, COUNT(*) FROM graph.graph_nodes GROUP BY node_type ORDER BY COUNT(*) DESC;")
            node_counts = cur.fetchall()
            cur.execute("SELECT edge_type, COUNT(*) FROM graph.graph_edges GROUP BY edge_type ORDER BY COUNT(*) DESC;")
            edge_counts = cur.fetchall()

            print("\n[node counts]")
            for nt, c in node_counts:
                print(f"- {nt}: {c}")
            print("\n[edge counts]")
            for et, c in edge_counts:
                print(f"- {et}: {c}")


if __name__ == "__main__":
    main()

