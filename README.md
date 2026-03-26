## DodgeAI — AI-powered O2C Graph Explorer

Explore an SAP Order-to-Cash (O2C) dataset as an **interactive graph** and ask **natural-language questions** with grounded, dataset-backed answers.

- **Demo**: `<add-your-single-demo-link-here>`
- **Core flow**: SalesOrder → OutboundDelivery → BillingDocument → JournalEntry → Payment

### Project Overview

- **What it does**:
  - Chat UI that answers O2C questions using **template-backed SQL** (optionally LLM-planned)
  - Graph UI that visualizes entities/relationships and supports **expand, filter, and highlight**
- **Why it’s useful**:
  - **Business**: quickly trace O2C exceptions (missing delivery/billing/payment) and audit document chains
  - **Technical**: combines relational data + graph traversal while keeping the system testable and deployable

### Architecture Decisions

- **FastAPI (backend)**:
  - Fast iteration (low boilerplate), strong request validation (Pydantic), async-friendly where needed
  - Clear API boundaries for a take-home: easy to test with OpenAPI/Swagger
- **React + graph visualization (frontend)**:
  - Interactive exploration (zoom/pan, hover tooltips, expand-on-click)
  - Implemented with a lightweight graph renderer (`react-cytoscapejs` + Cytoscape.js)
- **Separation of concerns**:
  - **Graph**: deterministic graph queries (neighbors/subgraph) and rendering concerns
  - **Chat**: query planning + guarded execution of allowlisted SQL templates
  - **Data layer**: raw ingestion + graph projection inside the same database
- **API-driven design**:
  - Browser never talks to the database directly
  - Enables independent deployment (Vercel/Render), and a consistent contract for UI + future clients

### Database Choice

- **Why PostgreSQL**:
  - Great for mixed workloads: relational joins + JSONB + recursive CTEs for graph-style expansion
  - Mature indexing and operational tooling
- **Why Neon**:
  - Serverless Postgres that’s quick to provision, easy to share for a demo, and scales without ops overhead
- **Why JSONB**:
  - SAP-like data is semi-structured; JSONB preserves source payloads while allowing selective indexing/querying
- **Normalization vs flexibility tradeoff**:
  - This project keeps **raw payloads** in `raw.*` and builds a **rebuildable graph projection** in `graph.*`
  - Tradeoff: some duplication, but consistent (single DB) and fast for graph queries

### LLM Prompting Strategy

- **Intent first, SQL second**:
  - User message → structured plan `{ template, params, limit }` (JSON)
  - Backend executes a **known SQL template** with validated parameters
- **Guarded prompting**:
  - LLM is only allowed to pick from a small list of templates (no free-form SQL)
  - If no template matches, the system rejects or asks for a dataset-relevant question
- **Avoiding hallucinations**:
  - Answers are generated from **actual query results**, not “best-effort” text
- **When LLM is used vs direct logic**:
  - With `OPENAI_API_KEY`: LLM helps map natural language → template choice/params
  - Without it: rule-based planner keeps behavior deterministic (still uses the same SQL templates)

### Guardrails

- **Out-of-domain rejection**: blocks prompts unrelated to the dataset (e.g., “write a story”)
- **Dataset-only grounding**: responses are tied to query outputs; no invented entities/relationships
- **Safety by design**: no arbitrary SQL execution; only allowlisted templates run server-side
- **Determinism where needed**: graph exploration and most query behavior remain predictable

### Key Features

- **Chat-based querying**: ask questions; see a grounded answer + optional tabular results
- **Graph visualization**: expand nodes, pan/zoom, hover for metadata tooltips, highlight relevant nodes
- **Relationship mapping**: filter edges by relationship type (e.g., `BILLED_AS`, `POSTED_AS`)
- **Granular vs high-level toggle**: hide/show detailed relationship overlays for readability

### Deployment

- **Frontend**: Vercel
- **Backend**: Render (FastAPI)
- **Database**: Neon (PostgreSQL)
- **Single demo link**:
  - The frontend calls the backend via `/api/*` (dev proxy + production rewrite)
  - Add your public demo URL at the top of this README

### How to Run Locally (short)

**Prereqs**: Python 3.11+ and Node 18+

**1) Backend**

From `Backend/`:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
