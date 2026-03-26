import type { TabularData } from "../../api/types";
import styles from "./DataTable.module.css";

function formatCell(value: unknown): string {
  if (value === null || value === undefined) return "";
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}

export function DataTable(props: { data: TabularData; maxRows?: number; maxHeightPx?: number }) {
  const maxRows = props.maxRows ?? 200;
  const maxHeightPx = props.maxHeightPx ?? 240;

  const columns = props.data.columns?.length
    ? props.data.columns
    : props.data.rows?.length
      ? Object.keys(props.data.rows[0] ?? {})
      : [];

  const visibleRows = props.data.rows.slice(0, maxRows);
  const showTruncation = props.data.rowCount > visibleRows.length;

  if (!columns.length) return null;

  return (
    <div className={styles.root}>
      <div className={styles.meta}>
        Rows: <b>{props.data.rowCount}</b>
        {showTruncation ? <span className={styles.trunc}> (showing first {visibleRows.length})</span> : null}
      </div>
      <div className={styles.wrap} style={{ maxHeight: `${maxHeightPx}px` }}>
        <table className={styles.table}>
          <thead>
            <tr>
              {columns.map((c) => (
                <th key={c}>{c}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {visibleRows.map((r, idx) => (
              <tr key={idx}>
                {columns.map((c) => (
                  <td key={c}>{formatCell(r[c])}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

