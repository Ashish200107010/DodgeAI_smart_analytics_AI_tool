## Backend (FastAPI)

### Setup

From `C:\projects\DodgeAI\Backend`:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Start Postgres + load dataset

- **Docker Postgres**: see `../docs/DB_SETUP.md` (recommended)
- After Postgres is running and tables are created, ingest:

```powershell
.\.venv\Scripts\python scripts\ingest_dataset.py
```

### Build graph projection (raw → graph)

After ingestion, build `graph.graph_nodes` and `graph.graph_edges`:

```powershell
.\.venv\Scripts\python scripts\build_graph_projection.py
```

Create a `.env` (you can copy `.env.example`) and set `DATABASE_URL`, e.g.:

```powershell
$env:DATABASE_URL="postgresql+psycopg://postgres:postgres@localhost:5432/dodgeai"
```

### Run server

```powershell
uvicorn app.main:app --reload --port 8000
```

Open docs: `http://127.0.0.1:8000/docs`

### Quick endpoint tests

Health:

```powershell
curl http://127.0.0.1:8000/api/health
```

Get a node (replace UUID):

```powershell
curl http://127.0.0.1:8000/api/graph/nodes/00000000-0000-0000-0000-000000000000
```

Neighbors:

```powershell
curl "http://127.0.0.1:8000/api/graph/nodes/00000000-0000-0000-0000-000000000000/neighbors?direction=both&includeGranular=false&limit=50"
```

Chat query:

```powershell
curl -X POST http://127.0.0.1:8000/api/chat/query -H "Content-Type: application/json" -d '{\"message\":\"91150187 - Find the journal entry linked to this?\"}'
```

Notes:
- Graph endpoints require `graph.graph_nodes` and `graph.graph_edges` to be populated.
- Chat endpoint will only answer a small set of template-backed questions until LLM planning is enabled.

