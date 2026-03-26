SELECT
  bh.billing_document AS "billingDocument",
  bh.accounting_document AS "accountingDocument",
  billing_node.node_id AS "billingDocumentNodeId",
  je_node.node_id AS "journalEntryNodeId"
FROM raw.billing_document_headers bh
LEFT JOIN raw.journal_entry_items_accounts_receivable je
  ON je.reference_document = bh.billing_document
 AND je.company_code = bh.company_code
 AND je.fiscal_year = bh.fiscal_year
 AND je.accounting_document = bh.accounting_document
LEFT JOIN graph.graph_nodes billing_node
  ON billing_node.node_key = CONCAT('BillingDocument:', bh.billing_document)
LEFT JOIN graph.graph_nodes je_node
  ON je_node.node_key = CONCAT(
    'JournalEntryItemAR:',
    je.company_code, '|', je.fiscal_year, '|', je.accounting_document, '|', je.accounting_document_item
  )
WHERE bh.billing_document = :billing_document
LIMIT :limit;

