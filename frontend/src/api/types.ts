export type UUID = string;

export type Degrees = {
  in: number;
  out: number;
  total: number;
};

export type GraphNode = {
  id: UUID;
  key: string;
  type: string;
  label: string;
  attrs: Record<string, unknown>;
  degrees?: Degrees;
};

export type GraphEdge = {
  id: UUID;
  typeId: UUID;
  typeCode: string;
  src: UUID;
  dst: UUID;
  evidence?: Record<string, unknown> | null;
};

export type GraphPayload = {
  nodes: GraphNode[];
  edges: GraphEdge[];
};

export type EdgeType = {
  id: UUID;
  code: string;
  displayName: string;
  description: string;
  srcNodeType: string | null;
  dstNodeType: string | null;
  isGranular: boolean;
  group: string;
};

export type ChatQueryRequest = {
  message: string;
  uiContext?: {
    focusedNodeId?: UUID | null;
    activeEdgeTypeIds?: UUID[] | null;
    hideGranularOverlay?: boolean | null;
  };
};

export type TabularData = {
  columns: string[];
  rows: Array<Record<string, unknown>>;
  rowCount: number;
};

export type ChatQueryResponse = {
  answer: string;
  rejected: boolean;
  rejectionReason?: string | null;
  data?: TabularData | null;
  highlights?: {
    focusNodeId?: UUID | null;
    highlightNodeIds?: UUID[];
    highlightEdgeIds?: UUID[];
  } | null;
};

export type GraphSubgraphRequest = {
  seedNodeIds: UUID[];
  maxHops?: number;
  edgeTypeIds?: UUID[] | null;
  includeGranular?: boolean;
  maxNodes?: number;
  maxEdges?: number;
};

