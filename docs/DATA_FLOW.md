## Data Flow (with example payloads)

This document shows **end-to-end data flow** for the two core user journeys, with concrete examples of the **data and formats** at each step.

Conventions used in examples:
- UUIDs shown are **example values** (your system will generate/return real UUIDs).
- Business identifiers shown (e.g., billing document `91150187`) are taken from the provided dataset.

---

## 1) Graph node expansion (UI → API → DB → UI)

### 1.1 UI bootstraps Mapping (relationship list)

**UI → API**

`GET /api/domain/edge-types`

**API → UI (example response)**

```json
[
  {
    "id": "2d0e0f1a-4c0d-4a68-9f38-4b4cc4c2f7a9",
    "code": "HAS_ITEM",
    "displayName": "Document has item",
    "description": "Parent document contains line-items",
    "srcNodeType": null,
    "dstNodeType": null,
    "isGranular": true,
    "group": "o2c_flow"
  },
  {
    "id": "e9b57d7f-3f1a-4d35-b0a2-88a6b03c2d8d",
    "code": "POSTED_AS",
    "displayName": "Billing posted as journal entry",
    "description": "Billing document posted into accounting document / journal entry",
    "srcNodeType": "BillingDocument",
    "dstNodeType": "JournalEntry",
    "isGranular": false,
    "group": "finance"
  }
]
```

**UI state derived from this**

```json
{
  "activeEdgeTypeIds": ["e9b57d7f-3f1a-4d35-b0a2-88a6b03c2d8d"],
  "hideGranularOverlay": true
}
```

---

### 1.2 User selects a node (loads node card)

Assume the user clicks a “Journal Entry” node.

**UI → API**

`GET /api/graph/nodes/d79e2d6a-5d7f-4d2a-8b4a-0f1e6c9a4a2a`

**API → DB (conceptual SQL)**

```sql
SELECT
  node_id,
  node_key,
  node_type,
  label,
  attrs
FROM graph.graph_nodes
WHERE node_id = :node_id;
```

**DB → API (row)**

```json
{
  "node_id": "d79e2d6a-5d7f-4d2a-8b4a-0f1e6c9a4a2a",
  "node_key": "JournalEntryItemAR:ABCD|2025|9400635958|1",
  "node_type": "JournalEntryItemAR",
  "label": "Journal Entry 9400635958 (Item 1)",
  "attrs": {
    "companyCode": "ABCD",
    "fiscalYear": "2025",
    "accountingDocument": "9400635958",
    "accountingDocumentItem": "1",
    "glAccount": "15500020",
    "referenceDocument": "91150187",
    "transactionCurrency": "INR",
    "amountInTransactionCurrency": -1167,
    "postingDate": "2025-04-02"
  }
}
```

**API → UI (Node payload example)**

```json
{
  "id": "d79e2d6a-5d7f-4d2a-8b4a-0f1e6c9a4a2a",
  "key": "JournalEntryItemAR:ABCD|2025|9400635958|1",
  "type": "JournalEntryItemAR",
  "label": "Journal Entry 9400635958 (Item 1)",
  "attrs": {
    "companyCode": "ABCD",
    "fiscalYear": "2025",
    "accountingDocument": "9400635958",
    "accountingDocumentItem": "1",
    "glAccount": "15500020",
    "referenceDocument": "91150187",
    "transactionCurrency": "INR",
    "amountInTransactionCurrency": -1167,
    "postingDate": "2025-04-02"
  },
  "degrees": { "in": 1, "out": 1, "total": 2 }
}
```

---

### 1.3 User expands the node (neighbors)

**UI → API**

`GET /api/graph/nodes/d79e2d6a-5d7f-4d2a-8b4a-0f1e6c9a4a2a/neighbors?direction=both&edgeTypeIds=e9b57d7f-3f1a-4d35-b0a2-88a6b03c2d8d&includeGranular=false&limit=200`

**API internal mapping**

The backend maps:

```json
{
  "edgeTypeIds": ["e9b57d7f-3f1a-4d35-b0a2-88a6b03c2d8d"],
  "edgeTypeCodes": ["POSTED_AS"]
}
```

**API → DB (conceptual SQL)**

```sql
SELECT edge_id, edge_type, src_node_id, dst_node_id, evidence
FROM graph.graph_edges
WHERE edge_type = ANY(:edge_type_codes)
  AND (
    src_node_id = :node_id
    OR dst_node_id = :node_id
  )
LIMIT :limit;
```

Then fetch involved nodes:

```sql
SELECT node_id, node_key, node_type, label, attrs
FROM graph.graph_nodes
WHERE node_id = ANY(:node_ids);
```

**DB → API (example rows)**

Edges:

```json
[
  {
    "edge_id": "0a6e3e2d-5c79-4f06-bc5c-0ad2c827c7f0",
    "edge_type": "POSTED_AS",
    "src_node_id": "b1f6f1a9-5ce7-4b20-8a2e-9e86a9a3b0b8",
    "dst_node_id": "d79e2d6a-5d7f-4d2a-8b4a-0f1e6c9a4a2a",
    "evidence": {
      "billingDocument": "91150187",
      "companyCode": "ABCD",
      "fiscalYear": "2025",
      "accountingDocument": "9400635958"
    }
  }
]
```

Nodes:

```json
[
  {
    "node_id": "b1f6f1a9-5ce7-4b20-8a2e-9e86a9a3b0b8",
    "node_key": "BillingDocument:91150187",
    "node_type": "BillingDocument",
    "label": "Billing 91150187",
    "attrs": {
      "billingDocumentType": "S1",
      "billingDocumentDate": "2025-04-02",
      "totalNetAmount": 329.66,
      "transactionCurrency": "INR",
      "companyCode": "ABCD",
      "fiscalYear": "2025",
      "accountingDocument": "9400635958",
      "soldToParty": "320000083"
    }
  },
  {
    "node_id": "d79e2d6a-5d7f-4d2a-8b4a-0f1e6c9a4a2a",
    "node_key": "JournalEntryItemAR:ABCD|2025|9400635958|1",
    "node_type": "JournalEntryItemAR",
    "label": "Journal Entry 9400635958 (Item 1)",
    "attrs": {
      "companyCode": "ABCD",
      "fiscalYear": "2025",
      "accountingDocument": "9400635958",
      "accountingDocumentItem": "1",
      "referenceDocument": "91150187"
    }
  }
]
```

**API → UI (GraphPayload example)**

```json
{
  "nodes": [
    {
      "id": "b1f6f1a9-5ce7-4b20-8a2e-9e86a9a3b0b8",
      "key": "BillingDocument:91150187",
      "type": "BillingDocument",
      "label": "Billing 91150187",
      "attrs": {
        "billingDocumentType": "S1",
        "billingDocumentDate": "2025-04-02",
        "totalNetAmount": 329.66,
        "transactionCurrency": "INR",
        "companyCode": "ABCD",
        "fiscalYear": "2025",
        "accountingDocument": "9400635958",
        "soldToParty": "320000083"
      },
      "degrees": { "in": 0, "out": 1, "total": 1 }
    },
    {
      "id": "d79e2d6a-5d7f-4d2a-8b4a-0f1e6c9a4a2a",
      "key": "JournalEntryItemAR:ABCD|2025|9400635958|1",
      "type": "JournalEntryItemAR",
      "label": "Journal Entry 9400635958 (Item 1)",
      "attrs": {
        "companyCode": "ABCD",
        "fiscalYear": "2025",
        "accountingDocument": "9400635958",
        "accountingDocumentItem": "1",
        "referenceDocument": "91150187"
      },
      "degrees": { "in": 1, "out": 1, "total": 2 }
    }
  ],
  "edges": [
    {
      "id": "0a6e3e2d-5c79-4f06-bc5c-0ad2c827c7f0",
      "typeId": "e9b57d7f-3f1a-4d35-b0a2-88a6b03c2d8d",
      "typeCode": "POSTED_AS",
      "src": "b1f6f1a9-5ce7-4b20-8a2e-9e86a9a3b0b8",
      "dst": "d79e2d6a-5d7f-4d2a-8b4a-0f1e6c9a4a2a",
      "evidence": {
        "billingDocument": "91150187",
        "companyCode": "ABCD",
        "fiscalYear": "2025",
        "accountingDocument": "9400635958"
      }
    }
  ]
}
```

**UI behavior**
- Merge nodes/edges into Cytoscape elements.
- Because the user selected a single relationship in Mapping, only edges with `typeId` in `activeEdgeTypeIds` are rendered.
- If `hideGranularOverlay=true`, the UI or API filters out `isGranular=true` relationship types.

---

## 2) Natural language query (UI → LLM → SQL → DB → response)

We’ll use a dataset-grounded example that matches the screenshot:

> “`91150187` – Find the journal entry number linked to this?”

From the dataset:
- `billing_document_headers.billingDocument = "91150187"`
- `billing_document_headers.accountingDocument = "9400635958"`
- `journal_entry_items_accounts_receivable.referenceDocument = "91150187"`
- `journal_entry_items_accounts_receivable.accountingDocument = "9400635958"`

### 2.1 UI → API request

`POST /api/chat/query`

```json
{
  "message": "91150187 - Find the journal entry number linked to this?",
  "uiContext": {
    "focusedNodeId": null,
    "activeEdgeTypeIds": ["e9b57d7f-3f1a-4d35-b0a2-88a6b03c2d8d"],
    "hideGranularOverlay": true
  }
}
```

---

### 2.2 API → LLM (planning) output: Query Plan JSON

The LLM returns a **structured plan** (no raw SQL execution privileges).

```json
{
  "intent": "lookup",
  "question": "Find journal entry linked to a billing document",
  "inputs": {
    "billingDocument": "91150187"
  },
  "querySpec": {
    "template": "billing_document_to_journal_entry",
    "returns": [
      { "name": "billingDocument", "type": "string" },
      { "name": "accountingDocument", "type": "string" },
      { "name": "journalEntryNodeId", "type": "uuid" }
    ],
    "limit": 10
  },
  "highlights": {
    "focus": "journalEntryNodeId",
    "alsoHighlight": ["billingDocumentNodeId"]
  }
}
```

---

### 2.3 API compiles plan → SQL (allowlisted template)

Example compiled SQL (conceptual):

```sql
SELECT
  bh.billing_document                                  AS "billingDocument",
  bh.accounting_document                               AS "accountingDocument",
  je_node.node_id                                      AS "journalEntryNodeId",
  billing_node.node_id                                 AS "billingDocumentNodeId"
FROM raw.billing_document_headers bh
JOIN raw.journal_entry_items_accounts_receivable je
  ON je.company_code = bh.company_code
 AND je.fiscal_year = bh.fiscal_year
 AND je.accounting_document = bh.accounting_document
 AND je.reference_document = bh.billing_document
JOIN graph.graph_nodes je_node
  ON je_node.node_key = CONCAT(
    'JournalEntryItemAR:',
    je.company_code, '|', je.fiscal_year, '|', je.accounting_document, '|', je.accounting_document_item
  )
JOIN graph.graph_nodes billing_node
  ON billing_node.node_key = CONCAT('BillingDocument:', bh.billing_document)
WHERE bh.billing_document = :billing_document
LIMIT :limit;
```

Parameters:

```json
{
  "billing_document": "91150187",
  "limit": 10
}
```

---

### 2.4 DB → API: result set (grounding data)

```json
{
  "columns": [
    "billingDocument",
    "accountingDocument",
    "journalEntryNodeId",
    "billingDocumentNodeId"
  ],
  "rows": [
    {
      "billingDocument": "91150187",
      "accountingDocument": "9400635958",
      "journalEntryNodeId": "d79e2d6a-5d7f-4d2a-8b4a-0f1e6c9a4a2a",
      "billingDocumentNodeId": "b1f6f1a9-5ce7-4b20-8a2e-9e86a9a3b0b8"
    }
  ],
  "rowCount": 1
}
```

---

### 2.5 API → LLM (answer synthesis) input/output

**LLM input (example)**

```json
{
  "instruction": "Answer using ONLY the rows provided. If empty/ambiguous, say so.",
  "rows": [
    {
      "billingDocument": "91150187",
      "accountingDocument": "9400635958"
    }
  ]
}
```

**LLM output (example)**

```text
The journal entry number linked to billing document 91150187 is 9400635958.
```

---

### 2.6 API → UI response (answer + highlights + optional subgraph)

```json
{
  "answer": "The journal entry number linked to billing document 91150187 is 9400635958.",
  "data": {
    "columns": ["billingDocument", "accountingDocument"],
    "rows": [{ "billingDocument": "91150187", "accountingDocument": "9400635958" }],
    "rowCount": 1
  },
  "highlights": {
    "focusNodeId": "d79e2d6a-5d7f-4d2a-8b4a-0f1e6c9a4a2a",
    "highlightNodeIds": [
      "b1f6f1a9-5ce7-4b20-8a2e-9e86a9a3b0b8",
      "d79e2d6a-5d7f-4d2a-8b4a-0f1e6c9a4a2a"
    ],
    "highlightEdgeIds": ["0a6e3e2d-5c79-4f06-bc5c-0ad2c827c7f0"]
  },
  "subgraph": {
    "nodes": [
      {
        "id": "b1f6f1a9-5ce7-4b20-8a2e-9e86a9a3b0b8",
        "key": "BillingDocument:91150187",
        "type": "BillingDocument",
        "label": "Billing 91150187",
        "attrs": { "companyCode": "ABCD", "fiscalYear": "2025" },
        "degrees": { "in": 0, "out": 1, "total": 1 }
      },
      {
        "id": "d79e2d6a-5d7f-4d2a-8b4a-0f1e6c9a4a2a",
        "key": "JournalEntryItemAR:ABCD|2025|9400635958|1",
        "type": "JournalEntryItemAR",
        "label": "Journal Entry 9400635958 (Item 1)",
        "attrs": { "referenceDocument": "91150187" },
        "degrees": { "in": 1, "out": 1, "total": 2 }
      }
    ],
    "edges": [
      {
        "id": "0a6e3e2d-5c79-4f06-bc5c-0ad2c827c7f0",
        "typeId": "e9b57d7f-3f1a-4d35-b0a2-88a6b03c2d8d",
        "typeCode": "POSTED_AS",
        "src": "b1f6f1a9-5ce7-4b20-8a2e-9e86a9a3b0b8",
        "dst": "d79e2d6a-5d7f-4d2a-8b4a-0f1e6c9a4a2a"
      }
    ]
  },
  "rejected": false,
  "rejectionReason": null
}
```

**UI behavior**
- Render `answer` in chat.
- If `subgraph` is present: merge into Cytoscape immediately.
- Highlight nodes/edges and **center on** `focusNodeId`.
- Open the node detail card for the focused node (like in the screenshot).

