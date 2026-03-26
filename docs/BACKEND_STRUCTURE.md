## Backend folder structure (Python + FastAPI)

Goal: a **production-ready but simple** layout that:
- keeps HTTP routing thin
- keeps DB access centralized and testable
- cleanly separates **graph exploration** from **conversational/LLM** logic
- makes it easy to add new edge types and new chat query templates

---

## Recommended structure (simple, scalable)

```text
backend/
  app/
    __init__.py
    main.py

    core/
      config.py
      logging.py
      errors.py

    api/
      deps.py
      routers/
        domain.py
        graph.py
        chat.py
      schemas/
        domain.py
        graph.py
        chat.py

    db/
      engine.py
      session.py
      run_sql.py
      sql/
        graph/
          get_node.sql
          neighbors.sql
          edges_by_type.sql
          search_nodes.sql
        chat/
          templates/
            billing_document_to_journal_entry.sql
            top_products_by_billing_docs.sql
            broken_flows.sql

    domain/
      edge_types.py
      node_types.py
      registry.py

    graph/
      repository.py
      service.py

    chat/
      service.py
      guardrails.py
      planner.py
      compiler/
        base.py
        registry.py
        templates/
          billing_document_to_journal_entry.py
          top_products_by_billing_docs.py
          broken_flows.py
      prompts/
        plan.md
        answer.md

    llm/
      client.py
      models.py

    util/
      ids.py
      pagination.py
      time.py 

    ingest/
      loader.py
      mappings.py

  scripts/
    ingest_dataset.py
    build_graph_projection.py

  tests/
    test_graph_repository.py
    test_chat_compilers.py
    test_guardrails.py

  pyproject.toml
  README.md
```

Notes:
- Keeping a `backend/` subproject is optional, but it’s clean when the repo also holds `docs/` and `dataset/`.
- This structure assumes Postgres contains `raw.*` and `graph.*` schemas.
- Bulk ingestion is script-driven (`backend/scripts/ingest_dataset.py`) so it doesn’t pollute the runtime graph/chat APIs.

---

## How to organize code responsibilities

### `app/api/*` (HTTP layer)

- **`api/routers/*`**: FastAPI routes only.
  - Should do: parse request, call a service, return a response.
  - Should NOT do: build SQL, call the LLM directly, implement business logic.
- **`api/schemas/*`**: Pydantic request/response models.
  - Keep them stable; avoid leaking DB column names when possible.
- **`api/deps.py`**: dependency injection (DB session, LLM client, config).

### Bulk ingestion (assignment-only, script-driven)

For this assignment, ingestion should be a **script** that reads from the repo’s `dataset/` folder (parallel to `backend/`) and loads into Postgres.

- **`scripts/ingest_dataset.py`**
  - Reads from `../dataset/...` (relative to `backend/`) and loads each dataset subfolder into its corresponding `raw.*` table.
  - After raw load, optionally triggers `scripts/build_graph_projection.py` to build `graph_nodes`/`graph_edges`.
  - Keep this script as a **dev/assignment utility**, not part of the runtime API surface.
- **`app/ingest/loader.py`**
  - Streaming JSONL reader
  - Bulk insert to Postgres (COPY or batched inserts)
  - Minimal validation (folder → table mapping, required key fields)
- **`app/ingest/mappings.py`**
  - Declares which dataset folder/file maps to which `raw.*` table
  - Defines primary keys and columns to promote vs keep in payload

This keeps ingestion concerns separate from the core runtime APIs and makes it easy to remove later.

### `app/services` vs per-domain services (`app/graph/service.py`, `app/chat/service.py`)

This layout uses **domain packages** (`graph/`, `chat/`) rather than a generic `services/` folder to keep separation obvious:
- **Graph service**: graph expansion/subgraph/search; never calls the LLM.
- **Chat service**: orchestrates guardrails → plan → compile → execute → grounded answer; may call graph service/repository to fetch a subgraph for highlights.

### `app/db/*` (database access)

- **`engine.py` / `session.py`**: create DB engine + session factory.
- **`run_sql.py`**: one place to execute parameterized SQL safely (and apply timeouts/row limits).
- **No direct DB calls** from routers; only repositories/services use `db/*`.

---

## Where to keep SQL queries / query builders

Use both patterns intentionally:

### 1) `.sql` files for “named queries” (recommended)

- Put SQL templates in `app/db/sql/...`.
- Keep each query small, parameterized, and named by use-case.
- Benefits:
  - easy to read and review
  - easy to test independently
  - avoids mixing SQL strings across code

### 2) Python query builders for dynamic filters (optional)

For queries that vary heavily by parameters (e.g., neighbor expansion with multiple filters), you can:
- use SQLAlchemy Core builders inside `graph/repository.py`, or
- keep a single SQL template and use safe “expanding” bind params.

Rule of thumb:
- **Graph queries**: often dynamic → repository/builders or templated SQL with safe binds.
- **Chat query templates**: should be allowlisted and stable → `.sql` templates + compiler wrapper.

---

## Separating graph logic vs conversational logic

### `app/graph/*` (graph exploration)

- **`graph/repository.py`**
  - contains DB queries against `graph.graph_nodes`, `graph.graph_edges`
  - returns domain-friendly objects (`Node`, `Edge`, `GraphPayload`)
- **`graph/service.py`**
  - enforces API-level policies (limits, filtering by edge types, hide granular overlay)
  - composes repository calls into responses

### `app/chat/*` (LLM + NL → SQL)

- **`chat/guardrails.py`**
  - rejects out-of-domain prompts
  - enforces “dataset-only” behavior
- **`chat/planner.py`**
  - calls the LLM to produce a **query plan JSON** (not raw SQL)
- **`chat/compiler/*`**
  - converts plan → SQL using allowlisted templates
  - validates that outputs are safe and match expected return shapes
- **`chat/service.py`**
  - orchestration: guardrails → plan → compile → execute → grounded answer → highlights/subgraph

Dependency direction best practice:
- `chat/*` may depend on `graph/*` (for highlights/subgraph).
- `graph/*` should not depend on `chat/*`.

---

## Domain registry (edge types, node types, mapping)

### Why `app/domain/*`

Both graph and chat need a shared understanding of:
- **edge types** (UUID id + code + isGranular + display metadata)
- **node types**
- mapping from `edgeTypeId (uuid)` → `edge_type code (string)` used in DB

Put these in:
- `domain/edge_types.py`: definitions
- `domain/registry.py`: helpers like:
  - `edge_type_id_for_code(code) -> uuid` (deterministic UUIDv5 recommended)
  - `edge_type_code_for_id(uuid) -> code`

---

## Best practices (maintainable + easy to extend)

- **Thin routers**
  - Routers call services; services call repositories; repositories call DB.
- **Strong typing at boundaries**
  - Pydantic schemas for all request/response payloads.
- **LLM safety**
  - LLM returns a **plan JSON**, not SQL.
  - Only execute SQL produced by your compiler/allowlist.
  - Always enforce limits/timeouts in `db/run_sql.py`.
- **Deterministic IDs**
  - Use UUIDv5 derived from `node_key` / `edge_key` when you want stable IDs across rebuilds.
- **One “place” for SQL**
  - Keep query templates in `app/db/sql/` and load them via helper.
- **Test strategy**
  - Unit test: compilers + guardrails (no DB needed).
  - Integration test: repository SQL (with a test DB or a small fixture).
- **Error handling**
  - Centralize HTTP error mapping in `core/errors.py` (domain errors → HTTP responses).
- **Observability (lightweight)**
  - Even if you skip telemetry, log: request id, chosen template, row counts, and execution time (helps debugging).

