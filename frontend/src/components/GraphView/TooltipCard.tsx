import styles from "./TooltipCard.module.css";

export type TooltipItem = { k: string; v: string };

export type TooltipState =
  | { visible: false }
  | {
      visible: true;
      x: number;
      y: number;
      title: string;
      subtitle?: string;
      items?: TooltipItem[];
    };

export function TooltipCard(props: { tooltip: TooltipState }) {
  if (!props.tooltip.visible) return null;

  const { x, y, title, subtitle, items } = props.tooltip;

  return (
    <div className={styles.root} style={{ left: x, top: y }}>
      <div className={styles.title}>{title}</div>
      {subtitle ? <div className={styles.subtitle}>{subtitle}</div> : null}
      {items?.length ? (
        <div className={styles.items}>
          {items.map((it) => (
            <div className={styles.item} key={it.k}>
              <div className={styles.k}>{it.k}</div>
              <div className={styles.v} title={it.v}>
                {it.v}
              </div>
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
}

