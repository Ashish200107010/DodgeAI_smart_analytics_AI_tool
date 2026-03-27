import { useEffect, useMemo, useState } from "react";
import { api } from "./api/client";
import type { EdgeType, UUID } from "./api/types";
import { ChatPanel } from "./components/ChatPanel/ChatPanel";
import { GraphView } from "./components/GraphView/GraphView";
import { NodeDetails } from "./components/NodeDetails/NodeDetails";
import styles from "./App.module.css";
import "./App.css";

export default function App() {
  const [edgeTypes, setEdgeTypes] = useState<EdgeType[]>([]);
  const [edgeTypesError, setEdgeTypesError] = useState<string | null>(null);

  const [hideGranularOverlay, setHideGranularOverlay] = useState(true);
  const [activeEdgeTypeIds, setActiveEdgeTypeIds] = useState<UUID[] | null>(null); // null = all

  const [selectedNodeId, setSelectedNodeId] = useState<UUID | null>(null);
  const [focusNodeId, setFocusNodeId] = useState<UUID | null>(null);

  useEffect(() => {
    api
      .listEdgeTypes()
      .then(setEdgeTypes)
      .catch((e) => setEdgeTypesError(e instanceof Error ? e.message : "Failed to load edge types"));
  }, []);

  const mappingOptions = useMemo(() => {
    const sorted = [...edgeTypes].sort((a, b) => a.displayName.localeCompare(b.displayName));
    return [{ id: "ALL", label: "All relationships" }, ...sorted.map((e) => ({ id: e.id, label: e.displayName }))];
  }, [edgeTypes]);

  return (
    <div className={styles.app}>
      <div className={styles.topbar}>
        <div className={styles.brand}>DodgeAI • O2C Graph</div>

        <div className={styles.controls}>
          <label className={styles.control}>
            <span>Relationship</span>
            <select
              value={activeEdgeTypeIds?.[0] ?? "ALL"}
              onChange={(e) => {
                const v = e.target.value;
                setActiveEdgeTypeIds(v === "ALL" ? null : [v]);
              }}
            >
              {mappingOptions.map((o) => (
                <option key={o.id} value={o.id}>
                  {o.label}
                </option>
              ))}
            </select>
          </label>

          <label className={styles.toggle}>
            <input
              type="checkbox"
              checked={hideGranularOverlay}
              onChange={(e) => setHideGranularOverlay(e.target.checked)}
            />
            <span>Hide granular overlay</span>
          </label>
        </div>
      </div>

      {edgeTypesError ? <div className={styles.bannerError}>{edgeTypesError}</div> : null}
      <div className={styles.bannerInfo}>Double refresh the page if not working..</div>
      <div className={styles.main}>
        <div className={styles.graphPane}>
          <GraphView
            edgeTypes={edgeTypes}
            activeEdgeTypeIds={activeEdgeTypeIds}
            hideGranularOverlay={hideGranularOverlay}
            focusNodeId={focusNodeId}
            onSelectionChange={(sel) => {
              if (sel.kind === "node") {
                setSelectedNodeId(sel.nodeId);
              }
            }}
          />

          <NodeDetails nodeId={selectedNodeId} />
        </div>

        <div className={styles.chatPane}>
          <ChatPanel
            edgeTypes={edgeTypes}
            activeEdgeTypeIds={activeEdgeTypeIds}
            hideGranularOverlay={hideGranularOverlay}
            onAnswerHighlights={(h) => {
              const focus = h?.focusNodeId ?? null;
              setFocusNodeId(focus);
              if (focus) setSelectedNodeId(focus);
            }}
          />
        </div>
      </div>
    </div>
  );
}
