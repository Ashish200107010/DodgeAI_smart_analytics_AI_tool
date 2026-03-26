## Tech Stack Plan (Option B: Raw SAP tables + Graph Projection)

This document captures the planned tech stack for the assignment and the rationale behind each choice.

## Context (what we’re building)

- **Goal**: A context-graph system with a **graph explorer UI** + **LLM-powered chat** that converts natural language → **structured SQL** → **grounded answers** (no hallucinations).
- **Data**: Structurally consistent SAP Order-to-Cash dataset folders (Sales Orders, Deliveries, Billing, Journal Entries, Payments, Business Partners, Products, Plants, etc.).
- **Chosen data approach (Option B)**:
  - Store the dataset **as-is** in SQL “raw” tables.
  - Build a **graph projection** as:
    - `graph_nodes`: pointer-like rows that map business entities to stable node IDs (and minimal display fields).
    - `graph_edges`: typed adjacency list (relationships) for fast graph expansion and path tracing.
  - Raw tables remain the **source of truth**; graph tables are a **rebuildable projection**.

## Recommended stack (default)

- **Database**: **PostgreSQL 16**
  - One DB instance, two schemas:
    - `raw.*` for tables mirroring the provided dataset
    - `graph.*` for `graph_nodes` / `graph_edges`
- **Backend API**: **Python 3.11+ + FastAPI**
  - **Validation**: Pydantic models for request/response + LLM query-plan JSON
  - **DB access**: SQLAlchemy Core (or `asyncpg` for thinner async access)
- **Frontend**: **React + Vite + TypeScript**
  - **Graph visualization**: Cytoscape.js
  - Optional component library (if desired): Mantine or MUI
- **LLM provider**: **OpenAI API**
  - Use structured JSON outputs for “NL → query plan”
  - Backend compiles plan → SQL, validates, executes, then synthesizes a grounded answer from returned rows
  - Alternative: Azure OpenAI (if enterprise constraints)
- **Local dev/deploy**: **Docker Compose**

## Why PostgreSQL (vs MySQL / SQL Server / Oracle)

### Why PostgreSQL is the best default here

- **Graph-style querying fits Postgres well**
  - This project needs graph-style operations (neighbor expansion, flow tracing, “broken flow” detection). Postgres supports:
    - **Recursive CTEs** (`WITH RECURSIVE`) for path/flow-style queries over `graph_edges`
    - Strong indexing patterns for adjacency tables (e.g., `(src_id, edge_type)`, `(dst_id, edge_type)`)
  - Postgres also handles mixed workloads well: many small indexed lookups (graph UI) + aggregations (top products, counts).
- **Best “power-to-friction” ratio**
  - Strong SQL features (CTEs, window functions, JSONB, constraints) and easy local setup via Docker.
- **Consistency + integrity tools**
  - Transactions and constraints support consistent “raw + projection” behavior (atomic rebuild/swap patterns are straightforward).
- **Ecosystem**
  - Excellent driver/ORM support across Python/Node and lots of examples for analytics and adjacency modeling.

### Why not MySQL (in this context)

- MySQL can do many things, but for “graph-ish + analytics” workloads, **complex CTE/analytic SQL tends to be less pleasant** than Postgres.
- You often end up moving more logic into the application layer earlier.

### Why not SQL Server (MSSQL) (in this context)

- Technically strong and absolutely viable, but typically **more friction** for a portable assignment demo (setup/tooling/licensing expectations vary).
- Great if your environment already standardizes on it; otherwise it’s heavier than needed.

### Why not Oracle (in this context)

- Very capable but **overkill** for an assignment: licensing + setup complexity with limited upside for this scope.

## Why Python + FastAPI (vs Spring Boot/Java and Node/JavaScript)

### Why Python + FastAPI is a strong choice here

- **Fastest path to a correct system**
  - Minimal boilerplate; quick iteration on the NL → plan → SQL → results → answer loop.
- **LLM integration is very ergonomic**
  - Strong ecosystem for structured outputs, validation, and orchestrating multi-step LLM calls safely.
- **Excellent query-plan validation**
  - Pydantic models make it hard to accidentally accept unsafe/unvalidated query plans.
- **Good fit for SQL-heavy logic**
  - Straightforward to generate/validate SQL (including recursive queries) and post-process results for grounded answers.

### Why not Spring Boot + Java (unless optimizing for enterprise patterns)

- **More upfront structure/ceremony**
  - Great for long-lived enterprise services, but slower to ship a polished prototype under time constraints.
- **LLM orchestration tends to be more verbose**
  - Still doable, but multi-step prompt flows + JSON-plan repair loops typically require more code.
- **When Java is a better pick**
  - If you prioritize strict compile-time types, standardized layered architecture, and enterprise packaging from day one.

### Why not Node + JavaScript (JS) (TypeScript changes the picture)

- **Pure JS** has weaker guarantees for safety-critical steps (plan validation, SQL allowlisting) unless you add strong runtime validation.
- Many Node ORMs abstract advanced SQL poorly; you’ll still need raw SQL for recursion/path queries.
- **Node + TypeScript is a valid alternative**
  - Strong option if you want one language across frontend/backend and real-time streaming chat UX.
  - Pair with strong validation (e.g., Zod) and a SQL approach that supports advanced SQL.

## Frontend choices (and alternatives)

### React + Vite + TypeScript

- **React** + **TypeScript** provides a clean UI foundation with strong typing for graph data payloads.
- **Vite** keeps the dev loop fast and simple.

### Cytoscape.js (graph visualization) vs React Flow

- **Cytoscape.js** is better for **graph exploration**: layouts, interaction patterns, and handling larger networks.
- **React Flow** is better for **diagramming/flow editors**, not large dynamic graph traversal.

## LLM integration approach (provider-agnostic, but simple)

- Use the LLM to produce a **structured query plan (JSON)**, not raw SQL.
- Deterministically compile plan → SQL, then **validate**:
  - allowlisted tables/columns/joins
  - read-only enforcement
  - LIMIT/timeouts
- Execute SQL, then provide results back to the LLM to generate a **grounded** answer.
- Guardrails reject out-of-domain prompts (“this system is designed for the dataset only”).

## Official documentation links

- **PostgreSQL**: [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- **Docker Compose**: [Docker Compose docs](https://docs.docker.com/compose/)
- **FastAPI**: [FastAPI docs](https://fastapi.tiangolo.com/)
- **SQLAlchemy**: [SQLAlchemy docs](https://docs.sqlalchemy.org/)
- **Pydantic**: [Pydantic docs](https://docs.pydantic.dev/)
- **asyncpg (optional)**: [asyncpg docs](https://magicstack.github.io/asyncpg/current/)
- **React**: [React docs](https://react.dev/)
- **Vite**: [Vite docs](https://vitejs.dev/)
- **TypeScript**: [TypeScript docs](https://www.typescriptlang.org/docs/)
- **Cytoscape.js**: [Cytoscape.js docs](https://js.cytoscape.org/)
- **React Flow (alternative)**: [React Flow docs](https://reactflow.dev/)
- **OpenAI API**: [OpenAI developer docs](https://platform.openai.com/docs/)
- **Azure OpenAI (alternative)**: [Azure OpenAI docs](https://learn.microsoft.com/azure/ai-services/openai/)

