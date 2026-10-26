import { arr, pretty, str } from "../utils.js";

export function Field({ label, hint, children }) {
  return (
    <label className="field">
      <span className="field-label">{label}</span>
      {children}
      {hint && <span className="field-hint">{hint}</span>}
    </label>
  );
}

export function Badge({ level }) {
  const l = str(level, "unknown").toLowerCase();
  return <span className={`badge badge-${l}`}>{pretty(l)}</span>;
}

export function Meter({ value, max = 100, tone }) {
  const pct = Math.max(0, Math.min(100, (Number(value) / max) * 100 || 0));
  return (
    <div className="meter" role="progressbar" aria-valuenow={Math.round(pct)} aria-valuemin={0} aria-valuemax={100}>
      <div className={`meter-fill ${tone || ""}`} style={{ width: `${pct}%` }} />
    </div>
  );
}

export function List({ items, ordered }) {
  const rows = arr(items).filter((x) => str(x).trim());
  if (!rows.length) return <p className="muted">Nothing to show.</p>;
  const Tag = ordered ? "ol" : "ul";
  return (
    <Tag className="list">
      {rows.map((x, i) => (
        <li key={i}>{str(x)}</li>
      ))}
    </Tag>
  );
}

/** Loading spinner, error box, and the demo / fallback / warning banners that every module shares. */
export function Feedback({ loading, error, meta, label = "Analysing…" }) {
  return (
    <>
      {loading && (
        <div className="spinner-row" role="status" aria-live="polite">
          <span className="spinner" /> {label}
        </div>
      )}
      {error && (
        <div className="alert alert-error" role="alert">
          <strong>Something went wrong.</strong> {error.message}
        </div>
      )}
      {!loading && meta?.mode === "demo" && (
        <div className="alert alert-demo">
          <strong>Demo mode.</strong> {meta.note}
        </div>
      )}
      {!loading && meta?.mode === "fallback" && (
        <div className="alert alert-warn">
          <strong>AI unavailable.</strong> {meta.note}
        </div>
      )}
      {!loading &&
        arr(meta?.warnings).map((w, i) => (
          <div className="alert alert-warn" key={i}>
            {str(w)}
          </div>
        ))}
    </>
  );
}

export function Empty({ children }) {
  return <div className="empty">{children}</div>;
}
