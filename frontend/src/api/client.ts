import type {
  ChatQueryRequest,
  ChatQueryResponse,
  EdgeType,
  GraphPayload,
  GraphSubgraphRequest,
  UUID,
} from "./types";

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });

  const text = await res.text();
  const data = text ? (JSON.parse(text) as unknown) : null;

  if (!res.ok) {
    const detail =
      typeof data === "object" && data && "detail" in (data as any)
        ? String((data as any).detail)
        : `${res.status} ${res.statusText}`;
    throw new Error(detail);
  }

  return data as T;
}

export const api = {
  health: () => requestJson<{ status: string }>("/api/health"),

  listEdgeTypes: () => requestJson<EdgeType[]>("/api/domain/edge-types"),

  getNode: (nodeId: UUID) => requestJson<any>(`/api/graph/nodes/${nodeId}`),

  getNeighbors: (nodeId: UUID, params: Record<string, string>) => {
    const qs = new URLSearchParams(params);
    return requestJson<GraphPayload>(`/api/graph/nodes/${nodeId}/neighbors?${qs.toString()}`);
  },

  subgraph: (body: GraphSubgraphRequest) =>
    requestJson<GraphPayload>("/api/graph/subgraph", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  chatQuery: (body: ChatQueryRequest) =>
    requestJson<ChatQueryResponse>("/api/chat/query", {
      method: "POST",
      body: JSON.stringify(body),
    }),
};

