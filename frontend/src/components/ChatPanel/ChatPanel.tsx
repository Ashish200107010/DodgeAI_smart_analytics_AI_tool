import { useMemo, useRef, useState } from "react";
import { api } from "../../api/client";
import type { ChatQueryResponse, EdgeType, TabularData, UUID } from "../../api/types";
import styles from "./ChatPanel.module.css";
import { DataTable } from "../DataTable/DataTable";

type ChatMessage =
  | { role: "user"; text: string }
  | { role: "assistant"; text: string; rejected?: boolean; table?: TabularData | null };

export function ChatPanel(props: {
  edgeTypes: EdgeType[];
  activeEdgeTypeIds: UUID[] | null;
  hideGranularOverlay: boolean;
  onAnswerHighlights: (highlights: ChatQueryResponse["highlights"] | null | undefined) => void;
}) {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: "assistant",
      text: "Ask a question about the SAP O2C dataset (e.g., “91150187 - Find the journal entry linked to this?”).",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const listRef = useRef<HTMLDivElement | null>(null);

  const canSend = input.trim().length > 0 && !loading;

  const helperText = useMemo(() => {
    if (!props.edgeTypes.length) return "Loading relationship types…";
    const activeCount = props.activeEdgeTypeIds?.length ?? 0;
    return `Mapping filter: ${activeCount ? activeCount : "all"} relationships • Granular overlay: ${
      props.hideGranularOverlay ? "hidden" : "shown"
    }`;
  }, [props.edgeTypes.length, props.activeEdgeTypeIds, props.hideGranularOverlay]);

  async function send() {
    const text = input.trim();
    if (!text) return;
    setInput("");
    setError(null);
    setLoading(true);
    setMessages((m) => [...m, { role: "user", text }]);

    try {
      const resp = await api.chatQuery({
        message: text,
        uiContext: {
          activeEdgeTypeIds: props.activeEdgeTypeIds,
          hideGranularOverlay: props.hideGranularOverlay,
        },
      });

      setMessages((m) => [
        ...m,
        {
          role: "assistant",
          text: resp.answer,
          rejected: resp.rejected,
          table: resp.data ?? null,
        },
      ]);

      props.onAnswerHighlights(resp.highlights);

      // Scroll to bottom after render
      queueMicrotask(() => {
        listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: "smooth" });
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Request failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className={styles.root}>
      <div className={styles.header}>
        <div>
          <div className={styles.title}>Chat</div>
          <div className={styles.subtitle}>{helperText}</div>
        </div>
      </div>

      <div className={styles.messages} ref={listRef}>
        {messages.map((m, idx) => (
          <div
            key={idx}
            className={`${styles.msg} ${m.role === "user" ? styles.user : styles.assistant}`}
          >
            <div className={styles.role}>{m.role === "user" ? "You" : "Dodge AI"}</div>
            <div className={styles.text}>
              {m.text}
              {"rejected" in m && m.rejected ? (
                <span className={styles.rejected}> (out of domain)</span>
              ) : null}
            </div>
            {"table" in m && m.table && m.table.columns?.length ? <DataTable data={m.table} /> : null}
          </div>
        ))}
      </div>

      {error ? <div className={styles.error}>{error}</div> : null}

      <div className={styles.composer}>
        <input
          className={styles.input}
          value={input}
          placeholder="Ask about orders, deliveries, billing, payments…"
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) send();
          }}
          disabled={loading}
        />
        <button className={styles.button} onClick={send} disabled={!canSend}>
          {loading ? "Sending…" : "Send"}
        </button>
      </div>

      <div className={styles.hint}>Tip: press Ctrl+Enter to send.</div>
    </div>
  );
}

