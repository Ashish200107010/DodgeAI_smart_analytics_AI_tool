## Local Postgres setup + load dataset (practical guide)

This guide sets up Postgres and loads the repo’s `dataset/` JSONL files into `raw.*` tables.

---

## Option A (recommended): Postgres with Docker Desktop

### 1) Install Docker Desktop (Windows)

- Install **Docker Desktop** and enable **WSL2** when prompted.
- After install, open a new terminal and verify:

```powershell
docker --version
docker compose version
```

### 2) Start Postgres

From `C:\projects\DodgeAI\Backend`:

```powershell
docker compose up -d
```

What this does:
- Starts `postgres:16` on `localhost:5432`
- Creates DB `dodgeai` (user/pass `postgres/postgres`)
- Runs `Backend/scripts/init_db.sql` automatically on first init (creates `raw` + `graph` schemas and tables)

To reset everything (deletes DB volume/data):

```powershell
docker compose down -v
docker compose up -d
```

### 3) Configure FastAPI DB connection

Create `Backend/.env` (copy from `.env.example`) and set:

```env
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/dodgeai
```

### 4) Ingest dataset into `raw.*`

From `C:\projects\DodgeAI\Backend` (venv activated):

```powershell
.\.venv\Scripts\python scripts\ingest_dataset.py
```

Default dataset path used by the script:
- `..\dataset\sap-order-to-cash-dataset\sap-o2c-data`

If needed, override:

```powershell
.\.venv\Scripts\python scripts\ingest_dataset.py --dataset-dir "..\dataset\sap-order-to-cash-dataset\sap-o2c-data"
```

### 5) Build the graph projection (`raw` → `graph`)

After `raw.*` is loaded:

```powershell
.\.venv\Scripts\python scripts\build_graph_projection.py
```

---

## Option B: Student-friendly hosted Postgres (no Docker)

If Docker isn’t available, use a free hosted Postgres and set `DATABASE_URL` to the provided connection string:
- **Neon**: `https://neon.tech/docs`
- **Supabase**: `https://supabase.com/docs/guides/database/overview`

Then run:

```powershell
psql "<your-connection-string>" -f Backend\scripts\init_db.sql
.\.venv\Scripts\python Backend\scripts\ingest_dataset.py --dataset-dir "dataset\sap-order-to-cash-dataset\sap-o2c-data"
```

---

## Verify data loaded (basic validation queries)

You can run SQL via:

```powershell
docker exec -it dodgeai-postgres psql -U postgres -d dodgeai
```

### Row counts

```sql
SELECT 'sales_order_headers' AS table, COUNT(*) FROM raw.sales_order_headers
UNION ALL SELECT 'sales_order_items', COUNT(*) FROM raw.sales_order_items
UNION ALL SELECT 'outbound_delivery_items', COUNT(*) FROM raw.outbound_delivery_items
UNION ALL SELECT 'billing_document_headers', COUNT(*) FROM raw.billing_document_headers
UNION ALL SELECT 'billing_document_items', COUNT(*) FROM raw.billing_document_items
UNION ALL SELECT 'journal_entry_items_ar', COUNT(*) FROM raw.journal_entry_items_accounts_receivable
UNION ALL SELECT 'payments_ar', COUNT(*) FROM raw.payments_accounts_receivable;
```

### Sample O2C join sanity check (Sales Order → Delivery)

```sql
SELECT
  soh.sales_order,
  COUNT(DISTINCT odi.delivery_document) AS delivery_count
FROM raw.sales_order_headers soh
JOIN raw.outbound_delivery_items odi
  ON odi.reference_sd_document = soh.sales_order
GROUP BY soh.sales_order
ORDER BY delivery_count DESC
LIMIT 10;
```

### Billing → Journal entry sanity check (example from dataset)

```sql
SELECT
  bh.billing_document,
  bh.accounting_document,
  je.accounting_document AS je_accounting_document
FROM raw.billing_document_headers bh
LEFT JOIN raw.journal_entry_items_accounts_receivable je
  ON je.reference_document = bh.billing_document
WHERE bh.billing_document = '91150187'
LIMIT 10;
```

