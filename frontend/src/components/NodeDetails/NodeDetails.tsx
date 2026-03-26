import { useEffect, useState } from "react";
import { api } from "../../api/client";
import type { UUID } from "../../api/types";
import styles from "./NodeDetails.module.css";

export function NodeDetails(props: { nodeId: UUID | null }) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [node, setNode] = useState<any>(null);

  useEffect(() => {
    if (!props.nodeId) {
      setNode(null);
      setError(null);
      return;
    }

    let canceled = false;
    setLoading(true);
    setError(null);

    api
      .getNode(props.nodeId)
      .then((n) => {
        if (!canceled) setNode(n);
      })
      .catch((e) => {
        if (!canceled) setError(e instanceof Error ? e.message : "Failed to load node");
      })
      .finally(() => {
        if (!canceled) setLoading(false);
      });

    return () => {
      canceled = true;
    };
  }, [props.nodeId]);

  return (
    <div className={styles.root}>
      <div className={styles.title}>Selection</div>
      {!props.nodeId ? (
        <div className={styles.empty}>Click a node to see metadata.</div>
      ) : loading ? (
        <div className={styles.empty}>Loading…</div>
      ) : error ? (
        <div className={styles.error}>{error}</div>
      ) : !node ? (
        <div className={styles.empty}>No data.</div>
      ) : (
        <div className={styles.card}>
          <div className={styles.kv}>
            <div className={styles.k}>Type</div>
            <div className={styles.v}>{String(node.type)}</div>
          </div>
          <div className={styles.kv}>
            <div className={styles.k}>Key</div>
            <div className={styles.v}>{String(node.key)}</div>
          </div>
          <div className={styles.kv}>
            <div className={styles.k}>Connections</div>
            <div className={styles.v}>
              {node.degrees ? `${node.degrees.total} (in ${node.degrees.in}, out ${node.degrees.out})` : "—"}
            </div>
          </div>

          <div className={styles.divider} />
          <div className={styles.attrsTitle}>Attrs</div>
          <pre className={styles.pre}>{JSON.stringify(node.attrs ?? {}, null, 2)}</pre>
        </div>
      )}
    </div>
  );
}

