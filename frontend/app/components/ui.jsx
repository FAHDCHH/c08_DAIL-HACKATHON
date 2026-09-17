"use client";

export function StatusBadge({ status, kind }) {
  // kind="status" → class "badge status-<status>" (event/report state);
  // no kind → class "badge <status>" (claim status). Label is always the plain value.
  const cls = kind ? `${kind}-${status}` : status;
  return <span className={`badge ${cls}`}>{status}</span>;
}

export function Skeleton({ lines = 3, height = 78 }) {
  return (
    <div aria-busy="true" role="status" aria-label="Loading">
      {Array.from({ length: lines }).map((_, i) => (
        <div key={i} className="skeleton" style={{ height }} />
      ))}
      <span className="sr-only">Loading…</span>
    </div>
  );
}

export function EmptyState({ title, hint, action }) {
  return (
    <div className="empty" role="status">
      <h3 className="empty-title">{title}</h3>
      {hint && <p className="empty-hint">{hint}</p>}
      {action}
    </div>
  );
}

export function ErrorState({ message, onRetry }) {
  return (
    <div className="errorstate" role="alert">
      <span>{message}</span>
      {onRetry && <button className="btn sec small" onClick={onRetry}>Try again</button>}
    </div>
  );
}

export function Toast({ toast }) {
  if (!toast) return null;
  return (
    <div className={`toast ${toast.err ? "err" : ""}`} role="status" aria-live="polite">
      {toast.msg}
    </div>
  );
}
