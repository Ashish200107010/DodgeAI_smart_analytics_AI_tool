## API Design (Graph + Mapping + Chat)

This document proposes the backend API needed to support:
- Graph exploration (expand/inspect/path)
- The **Mapping → relationship** filter (show only selected relationships)
- Chat-driven queries that return **grounded answers + highlighted nodes** in the graph

Assumptions:
- Postgres stores `raw.*` tables and the graph projection in `graph.graph_nodes` / `graph.graph_edges`.
- `graph.graph_nodes.node_id` is a **UUID** and is the canonical identifier used by the UI.
- The UI renders graphs from **nodes + edges** payloads (Cytoscape-friendly).

---

## Core payload shapes

### Node

- **`id`**: uuid (maps to `graph_nodes.node_id`)
- **`key`**: string (maps to `graph_nodes.node_key`, deterministic/business-readable)
- **`type`**: string (`node_type`)
- **`label`**: string (human-readable label)
- **`attrs`**: object (small preview set for tooltips/cards)
- **`degrees`**: object `{ in: int, out: int, total: int }` (for “Connections: N” in the UI)

### Edge

- **`id`**: uuid (maps to `graph_edges.edge_id`)
- **`typeId`**: uuid (ID of the relationship type; derived from EdgeType.id)
- **`typeCode`**: string (`edge_type` code; used for display/debug)
- **`src`**: uuid (`src_node_id`)
- **`dst`**: uuid (`dst_node_id`)
- **`evidence`**: object (optional; shows why/how nodes are connected)

### GraphPayload

- **`nodes`**: Node[]
- **`edges`**: Edge[]

### EdgeType (relationship metadata)

Used to populate the Mapping UI and to implement “Hide Granular Overlay”.

- **`id`**: uuid (stable ID for the relationship type)
- **`code`**: string (the `edge_type` value used in storage/debug)
- **`displayName`**: string (UI name)
- **`description`**: string (short explanation)
- **`srcNodeType`**: string | null
- **`dstNodeType`**: string | null
- **`isGranular`**: boolean (true = noisy/item-level relationships)
- **`group`**: string (e.g., `o2c_flow`, `master_data`, `inventory`, `finance`)

---

## Domain + Mapping endpoints

### `GET /api/domain/edge-types`

Returns EdgeType[] for:
- relationship picker (“Mapping”)
- filtering edges in the graph
- implementing “Hide Granular Overlay” (filter out `isGranular=true`)

### `GET /api/domain/node-types` (optional)

Returns node-type metadata for UI rendering (icons/colors) and search filters.

---

## Graph exploration endpoints

### `GET /api/graph/nodes/{nodeId}`

Returns a single Node (with `attrs` preview + degree counts). Used for node cards like the “Journal Entry” popover in the screenshot.

### `GET /api/graph/nodes/{nodeId}/neighbors`

Expands a node.

Query params:
- `direction`: `out` | `in` | `both` (default `both`)
- `edgeTypeIds`: repeated param or comma-separated list of UUIDs (optional)
- `includeGranular`: boolean (default true; if false, exclude granular edge types)
- `limit`: integer (default 200)

Response: GraphPayload (neighbors + connecting edges)

### `POST /api/graph/subgraph`

Fetch a small graph region for rendering/highlighting.

Body:
- `seedNodeIds`: uuid[]
- `maxHops`: int (e.g., 1–4)
- `edgeTypeIds`: uuid[] (optional)
- `includeGranular`: boolean
- `maxNodes`: int
- `maxEdges`: int

Response: GraphPayload

### `GET /api/graph/edges`

Supports the Mapping UI when the user selects a single relationship and wants to “show only that relationship”.

Query params:
- `edgeTypeId`: uuid (required)
- `includeNodes`: boolean (default true; include endpoint nodes so UI can render immediately)
- `limit`: int (default 2000)
- `cursor`: string (optional; for pagination)

Response:
- `graph`: GraphPayload
- `nextCursor`: string | null

### `GET /api/graph/search` (optional but practical)

Find nodes by business IDs or human labels (useful when the chat returns a key and the UI needs to locate it).

Query params:
- `q`: string
- `nodeTypes`: string[] (optional)
- `limit`: int

Response: Node[] (thin payload: `id`, `key`, `type`, `label`)

---

## Chat / LLM endpoints

### `POST /api/chat/query`

Body:
- `message`: string
- `uiContext` (optional):
  - `focusedNodeId`: uuid | null (selected node in graph)
  - `activeEdgeTypeIds`: uuid[] | null (Mapping filter state)
  - `hideGranularOverlay`: boolean | null

Response:
- `answer`: string (grounded)
- `data` (optional):
  - `columns`: string[]
  - `rows`: object[]
  - `rowCount`: int
- `highlights` (optional):
  - `focusNodeId`: uuid | null
  - `highlightNodeIds`: uuid[]
  - `highlightEdgeIds`: uuid[]
- `subgraph` (optional): GraphPayload (enough nodes/edges to render the highlight region)
- `rejected`: boolean
- `rejectionReason`: string | null

Notes:
- To satisfy the “highlight node after answering” requirement, the backend should **derive highlight node IDs from query results** (e.g., select/join `graph_nodes.node_id`), not from free-form LLM guesses.
- When a query returns a single best node (like “journal entry linked to billing document X”), set `focusNodeId` so the UI can auto-center/zoom and open the node card.

---

## UI feature mapping (from screenshots)

- **Mapping → relationship selector**
  - UI calls `GET /api/domain/edge-types`
  - Selecting one relationship calls `GET /api/graph/edges?edgeTypeId=...` (or filters locally if already loaded)
- **Hide Granular Overlay**
  - UI filters edge types where `isGranular=true`, or requests `includeGranular=false` on graph endpoints
- **Highlight after answering**
  - Chat response includes `highlights.focusNodeId` and `highlights.highlightNodeIds`
  - UI highlights/centers those nodes in Cytoscape and opens the node detail card (like the “Journal Entry” popover)

