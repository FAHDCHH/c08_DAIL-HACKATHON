"use client";
import { useEffect, useState } from "react";
import { api } from "../../lib/api";
import { EmptyState, ErrorState, Skeleton, StatusBadge } from "./ui";

export default function Events({ onOpen }) {
  const [q, setQ] = useState("");
  const [rows, setRows] = useState(null);
  const [error, setError] = useState(null);

  const load = async (query = "") => {
    setError(null);
    try { setRows(await api.events(query)); }
    catch (e) { setError(e.message); setRows([]); }
  };
  useEffect(() => { load(); }, []);

  return (
    <main className="wrap">
      <header className="pagehead">
        <span className="eyebrow">Programme reporting</span>
        <h1>Programme events</h1>
        <p>Each event holds the field reports received about it. Open one to build its evidence-based report.</p>
      </header>

      <div className="searchbar" style={{ marginBottom: 18, maxWidth: 440 }}>
        <input aria-label="Search events by name" placeholder="Search events by name…" value={q}
          onChange={(e) => { setQ(e.target.value); load(e.target.value); }} />
      </div>

      {rows === null && <Skeleton lines={3} />}
      {error && <ErrorState message={"Could not load events: " + error} onRetry={() => load(q)} />}
      {rows && !error && rows.length === 0 && (
        <EmptyState title={q ? "No matching events" : "No events yet"}
          hint={q ? "Try a different search." : "Events appear here as reports are received."} />
      )}

      {rows && rows.length > 0 && (
        <ul className="u-list">
          {rows.map((e, i) => (
            <li key={e.event_id}>
              <button className="card eventcard" style={{ animationDelay: `${Math.min(i * 70, 420)}ms` }}
                onClick={() => onOpen(e.event_id)}
                aria-label={`Open ${e.title}, status ${e.report_status}${e.needs_attention ? `, ${e.new_reports} new reports need attention` : ""}`}>
                <span className="grow">
                  <span className="eventcard-title">{e.title}</span>
                  <span className="meta">{e.program} · {e.period} · {e.total_reports} report(s)</span>
                </span>
                <StatusBadge status={e.report_status} kind="status" />
                {e.needs_attention
                  ? <span className="pill-attn">{e.new_reports} new · needs report</span>
                  : <span className="pill-ok">up to date</span>}
              </button>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
