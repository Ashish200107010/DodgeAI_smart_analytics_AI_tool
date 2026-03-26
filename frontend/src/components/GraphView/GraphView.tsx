import CytoscapeComponent from "react-cytoscapejs";
import cytoscape, { type Core, type ElementDefinition, type EventObject } from "cytoscape";
import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "../../api/client";
import type { EdgeType, GraphPayload, UUID } from "../../api/types";
import styles from "./GraphView.module.css";
import { TooltipCard, type TooltipItem, type TooltipState } from "./TooltipCard";

cytoscape.warnings(false);

type GraphSelection =
  | { kind: "none" }
  | { kind: "node"; nodeId: UUID; nodeKey: string; nodeType: string }
  | { kind: "edge"; edgeId: UUID; typeCode: string };

function toElements(payload: GraphPayload): ElementDefinition[] {
  const nodes: ElementDefinition[] = payload.nodes.map((n) => ({
    data: {
      id: n.id,
      label: n.label,
      key: n.key,
      type: n.type,
      attrs: n.attrs,
    },
  }));

  const edges: ElementDefinition[] = payload.edges.map((e) => ({
    data: {
      id: e.id,
      source: e.src,
      target: e.dst,
      typeId: e.typeId,
      typeCode: e.typeCode,
      evidence: e.evidence ?? undefined,
    },
  }));

  return [...nodes, ...edges];
}

function scoreKey(key: string): number {
  const k = key.toLowerCase();
  let s = 0;
  if (k.includes("amount") || k.includes("net") || k.includes("gross") || k.includes("total")) s += 6;
  if (k.includes("currency")) s += 5;
  if (k.includes("date") || k.includes("time")) s += 5;
  if (k.includes("status")) s += 4;
  if (k.includes("qty") || k.includes("quantity")) s += 3;
  if (k.includes("customer") || k.includes("soldto") || k.includes("partner")) s += 3;
  if (k.includes("company") || k.includes("plant") || k.includes("storage")) s += 2;
  if (k.includes("document") || k.includes("order") || k.includes("delivery") || k.includes("billing")) s += 2;
  return s;
}

function fmtValue(v: unknown): string {
  if (v === null || v === undefined) return "";
  if (typeof v === "string") return v;
  if (typeof v === "number" || typeof v === "boolean") return String(v);
  if (Array.isArray(v)) return v.length <= 6 ? `[${v.map((x) => fmtValue(x)).join(", ")}]` : `[${v.length} items]`;
  try {
    return JSON.stringify(v);
  } catch {
    return String(v);
  }
}

function pickRelevant(obj: unknown, maxItems: number): TooltipItem[] {
  if (!obj || typeof obj !== "object") return [];
  const rec = obj as Record<string, unknown>;

  const entries = Object.entries(rec)
    .map(([k, v]) => [k, fmtValue(v)] as const)
    .filter(([k, v]) => Boolean(k) && v !== "" && v !== "null" && v !== "undefined");

  const scored = entries.map(([k, v]) => ({ k, v, s: scoreKey(k) }));
  const hasAnySignal = scored.some((e) => e.s > 0);
  scored.sort((a, b) => (b.s - a.s) || a.k.localeCompare(b.k));

  const chosen = (hasAnySignal ? scored.filter((e) => e.s > 0) : scored).slice(0, maxItems);
  return chosen.map((e) => ({ k: e.k, v: e.v }));
}

export function GraphView(props: {
  edgeTypes: EdgeType[];
  activeEdgeTypeIds: UUID[] | null;
  hideGranularOverlay: boolean;
  focusNodeId: UUID | null;
  onSelectionChange: (sel: GraphSelection) => void;
}) {
  const cyRef = useRef<cytoscape.Core | null>(null);
  const canvasRef = useRef<HTMLDivElement | null>(null);
  const [tooltip, setTooltip] = useState<TooltipState>({ visible: false });
  const showTimerRef = useRef<number | null>(null);
  const hideTimerRef = useRef<number | null>(null);
  const rafRef = useRef<number | null>(null);
  const latestPosRef = useRef<{ x: number; y: number } | null>(null);
  const hoverKeyRef = useRef<string | null>(null); // "node:<id>" | "edge:<id>"
  const activeEdgeTypeIdsRef = useRef<UUID[] | null>(props.activeEdgeTypeIds);
  const hideGranularOverlayRef = useRef<boolean>(props.hideGranularOverlay);
  const onSelectionChangeRef = useRef(props.onSelectionChange);

  function clearTimers() {
    if (showTimerRef.current) window.clearTimeout(showTimerRef.current);
    if (hideTimerRef.current) window.clearTimeout(hideTimerRef.current);
    showTimerRef.current = null;
    hideTimerRef.current = null;
  }

  useEffect(() => {
    activeEdgeTypeIdsRef.current = props.activeEdgeTypeIds;
  }, [props.activeEdgeTypeIds]);

  useEffect(() => {
    hideGranularOverlayRef.current = props.hideGranularOverlay;
  }, [props.hideGranularOverlay]);

  useEffect(() => {
    onSelectionChangeRef.current = props.onSelectionChange;
  }, [props.onSelectionChange]);

  useEffect(() => {
    return () => {
      clearTimers();
      if (rafRef.current !== null) window.cancelAnimationFrame(rafRef.current);
    };
  }, []);

  function clampToCanvas(x: number, y: number) {
    const el = canvasRef.current;
    if (!el) return { x, y };
    const w = el.clientWidth;
    const h = el.clientHeight;
    const pad = 10;
    const tooltipW = 320;
    // rough height cap; content varies but this prevents obvious off-screen placement
    const tooltipH = 220;
    return {
      x: Math.max(pad, Math.min(x, Math.max(pad, w - tooltipW - pad))),
      y: Math.max(pad, Math.min(y, Math.max(pad, h - tooltipH - pad))),
    };
  }

  function schedulePosUpdate() {
    if (rafRef.current !== null) return;
    rafRef.current = window.requestAnimationFrame(() => {
      rafRef.current = null;
      const p = latestPosRef.current;
      if (!p) return;
      const clamped = clampToCanvas(p.x, p.y);
      setTooltip((t) => (t.visible ? { ...t, x: clamped.x, y: clamped.y } : t));
    });
  }

  const stylesheet = useMemo(
    () => [
      {
        selector: "node",
        style: {
          "background-color": "#1f6feb",
          "border-width": 1,
          "border-color": "rgba(0,0,0,0.25)",
          label: "data(label)",
          color: "rgba(0,0,0,0.78)",
          "font-size": 10,
          "text-valign": "center",
          "text-halign": "center",
          "text-wrap": "wrap",
          "text-max-width": 100,
          "text-outline-width": 2,
          "text-outline-color": "rgba(255,255,255,0.9)",
        },
      },
      {
        selector: "edge",
        style: {
          width: 1,
          "line-color": "rgba(31,111,235,0.35)",
          "target-arrow-shape": "triangle",
          "target-arrow-color": "rgba(31,111,235,0.35)",
          "curve-style": "bezier",
          // Make thin edges easier to hover/click without changing visuals much.
          "overlay-padding": 6,
          "overlay-opacity": 0,
        },
      },
      {
        selector: "node.highlight",
        style: {
          "border-width": 3,
          "border-color": "#ffb000",
          opacity: 1,
        },
      },
      {
        selector: ".filteredOut",
        style: { display: "none" },
      },
      {
        selector: ".granularHidden",
        style: { display: "none" },
      },
    ],
    []
  );

  // Seed the graph with a small subgraph when focusNodeId changes.
  useEffect(() => {
    const focus = props.focusNodeId;
    if (!focus) return;
    const cy = cyRef.current;
    if (!cy) return;

    let canceled = false;
    (async () => {
      try {
        const payload = await api.subgraph({
          seedNodeIds: [focus],
          maxHops: 3,
          includeGranular: !props.hideGranularOverlay,
          edgeTypeIds: props.activeEdgeTypeIds,
          maxNodes: 300,
          maxEdges: 800,
        });

        if (canceled) return;

        cy.batch(() => {
          cy.add(toElements(payload));
        });
        cy.layout({ name: "cose", animate: true, fit: true }).run();
        cy.nodes().removeClass("highlight");
        cy.getElementById(focus).addClass("highlight");
        cy.center(cy.getElementById(focus));
      } catch {
        // ignore: graph might not be ready
      }
    })();

    return () => {
      canceled = true;
    };
  }, [props.focusNodeId, props.activeEdgeTypeIds, props.hideGranularOverlay]);

  // Hide/show granular overlay edges (client-side) so toggling works even if graph already has edges.
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;

    const granularTypeIds = new Set(props.edgeTypes.filter((e) => e.isGranular).map((e) => e.id));

    cy.batch(() => {
      cy.edges().removeClass("granularHidden");
      if (!props.hideGranularOverlay) return;

      cy.edges().forEach((e) => {
        const typeId = String(e.data("typeId"));
        if (granularTypeIds.has(typeId)) {
          e.addClass("granularHidden");
        }
      });
    });
  }, [props.hideGranularOverlay, props.edgeTypes]);

  // Apply mapping filter (show only selected relationship type(s)).
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;

    const active = props.activeEdgeTypeIds;
    if (!active || active.length === 0) {
      cy.elements().removeClass("filteredOut");
      return;
    }

    const activeSet = new Set(active);
    cy.batch(() => {
      cy.elements().addClass("filteredOut");
      // Always keep highlighted nodes visible (chat focus / user selection).
      cy.nodes(".highlight").removeClass("filteredOut");
      cy.edges().forEach((e) => {
        const typeId = String(e.data("typeId"));
        if (activeSet.has(typeId)) {
          e.removeClass("filteredOut");
          e.source().removeClass("filteredOut");
          e.target().removeClass("filteredOut");
        }
      });
    });
  }, [props.activeEdgeTypeIds]);

  // Node click => expand neighbors
  async function expandNode(nodeId: UUID) {
    const cy = cyRef.current;
    if (!cy) return;

    const params: Record<string, string> = {
      direction: "both",
      includeGranular: hideGranularOverlayRef.current ? "false" : "true",
      limit: "200",
    };
    const active = activeEdgeTypeIdsRef.current;
    if (active && active.length) {
      // URLSearchParams supports repeated keys; we encode as CSV for simplicity (backend supports list via FastAPI Query)
      // For Postman-style repetition, a client would append multiple edgeTypeIds.
      params.edgeTypeIds = active.join(",");
    }

    const payload = await api.getNeighbors(nodeId, params);
    cy.batch(() => {
      cy.add(toElements(payload));
    });
    cy.layout({ name: "cose", animate: true, fit: false }).run();
  }

  return (
    <div className={styles.root}>
      <div className={styles.header}>
        <div>
          <div className={styles.title}>Graph</div>
          <div className={styles.subtitle}>
            Click a node to expand. Chat answers can highlight nodes.
          </div>
        </div>
      </div>

      <div className={styles.canvas} ref={canvasRef}>
        <CytoscapeComponent
          elements={[]}
          cy={(cy: Core) => {
            cyRef.current = cy;

            // ---- Hover tooltips (nodes + edges) ----
            const showDelayMs = 120;
            const hideDelayMs = 140;

            cy.off("mouseover", "node");
            cy.off("mousemove", "node");
            cy.off("mouseout", "node");
            cy.off("mouseover", "edge");
            cy.off("mousemove", "edge");
            cy.off("mouseout", "edge");
            cy.off("tap", "node");
            cy.off("tap", "edge");

            function show(tt: Omit<Extract<TooltipState, { visible: true }>, "visible">, hoverKey: string) {
              clearTimers();
              hoverKeyRef.current = hoverKey;
              showTimerRef.current = window.setTimeout(() => {
                if (hoverKeyRef.current !== hoverKey) return;
                const clamped = clampToCanvas(tt.x, tt.y);
                setTooltip({ visible: true, ...tt, x: clamped.x, y: clamped.y });
              }, showDelayMs);
            }

            function hide(hoverKey: string) {
              if (hoverKeyRef.current !== hoverKey) return;
              clearTimers();
              hideTimerRef.current = window.setTimeout(() => {
                if (hoverKeyRef.current !== hoverKey) return;
                hoverKeyRef.current = null;
                setTooltip({ visible: false });
              }, hideDelayMs);
            }

            function updatePos(evt: EventObject, hoverKey: string) {
              if (hoverKeyRef.current !== hoverKey) return;
              const rp = (evt as any).renderedPosition as { x: number; y: number } | undefined;
              if (!rp) return;
              latestPosRef.current = { x: rp.x + 12, y: rp.y + 12 };
              schedulePosUpdate();
            }

            cy.on("mouseover", "node", (evt: EventObject) => {
              const n = evt.target as cytoscape.NodeSingular;
              const id = String(n.id());
              const type = String(n.data("type") ?? "");
              const label = String(n.data("label") ?? id);
              const attrs = n.data("attrs") as unknown;
              const items = pickRelevant(attrs, 8);
              const rp = (evt as any).renderedPosition as { x: number; y: number } | undefined;
              const x = (rp?.x ?? 0) + 12;
              const y = (rp?.y ?? 0) + 12;
              show(
                {
                  x,
                  y,
                  title: label,
                  subtitle: `${type || "Node"} · ${id}`,
                  items,
                },
                `node:${id}`
              );
            });

            cy.on("mousemove", "node", (evt: EventObject) => {
              const n = evt.target as cytoscape.NodeSingular;
              updatePos(evt, `node:${String(n.id())}`);
            });

            cy.on("mouseout", "node", (evt: EventObject) => {
              const n = evt.target as cytoscape.NodeSingular;
              hide(`node:${String(n.id())}`);
            });

            cy.on("mouseover", "edge", (evt: EventObject) => {
              const e = evt.target as cytoscape.EdgeSingular;
              const id = String(e.id());
              const typeCode = String(e.data("typeCode") ?? "EDGE");
              const srcLabel = String(e.source().data("label") ?? e.source().id());
              const dstLabel = String(e.target().data("label") ?? e.target().id());
              const evidence = e.data("evidence") as unknown;
              const items = pickRelevant(evidence, 6);
              const rp = (evt as any).renderedPosition as { x: number; y: number } | undefined;
              const x = (rp?.x ?? 0) + 12;
              const y = (rp?.y ?? 0) + 12;
              show(
                {
                  x,
                  y,
                  title: typeCode,
                  subtitle: `${srcLabel} → ${dstLabel}`,
                  items,
                },
                `edge:${id}`
              );
            });

            cy.on("mousemove", "edge", (evt: EventObject) => {
              const e = evt.target as cytoscape.EdgeSingular;
              updatePos(evt, `edge:${String(e.id())}`);
            });

            cy.on("mouseout", "edge", (evt: EventObject) => {
              const e = evt.target as cytoscape.EdgeSingular;
              hide(`edge:${String(e.id())}`);
            });

            cy.on("tap", "node", async (evt: EventObject) => {
              const n = evt.target as cytoscape.NodeSingular;
              const id = String(n.id());
              onSelectionChangeRef.current({
                kind: "node",
                nodeId: id,
                nodeKey: String(n.data("key") ?? ""),
                nodeType: String(n.data("type") ?? ""),
              });

              n.addClass("highlight");
              await expandNode(id);
            });

            cy.on("tap", "edge", (evt: EventObject) => {
              const e = evt.target as cytoscape.EdgeSingular;
              onSelectionChangeRef.current({
                kind: "edge",
                edgeId: String(e.id()),
                typeCode: String(e.data("typeCode") ?? ""),
              });
            });
          }}
          style={{ width: "100%", height: "100%" }}
          // react-cytoscapejs types are strict; styles are still valid for cytoscape runtime.
          stylesheet={stylesheet as any}
        />

        <TooltipCard tooltip={tooltip} />
      </div>
    </div>
  );
}

