"use client";
import { useEffect, useState } from "react";
import { api } from "../../lib/api";
import { EmptyState, ErrorState, Skeleton } from "./ui";

export default function History({ flash }) {
  const [q, setQ] = useState("");
  const [rows, setRows] = useState(null);
  const [error, setError] = useState(null);

  const load = async (query = "") => {
    setError(null);
    try { setRows(await api.history(query)); } catch (e) { setError(e.message); setRows([]); }
  };
  useEffect(() => { load(); }, []);

  return (
    <main className="wrap">
      <header className="pagehead">
        <span className="eyebrow">Archive</span>
        <h1>Report history</h1>
        <p>Every report the agent generated. Search by event name and download the PDF.</p>
      </header>

      <div className="searchbar" style={{ marginBottom: 18, maxWidth: 440 }}>
        <input aria-label="Search reports by event name" placeholder="Search by event name…" value={q}
          onChange={(e) => { setQ(e.target.value); load(e.target.value); }} />
      </div>

      {rows === null && <Skeleton lines={4} height={46} />}
      {error && <ErrorState message={"Could not load history: " + error} onRetry={() => load(q)} />}
      {rows && !error && rows.length === 0 && (
        <EmptyState title={q ? "No matching reports" : "No generated reports yet"}
          hint={q ? "Try a different search." : "Approve or revise a report to see it here."} />
      )}

      {rows && rows.length > 0 && (
        <table className="htable">
          <caption className="sr-only">Generated reports, newest first</caption>
          <thead><tr><th scope="col">#</th><th scope="col">Event</th><th scope="col">Kind</th><th scope="col">Generated</th><th scope="col"><span className="sr-only">Download</span></th></tr></thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.generated_id}>
                <td>{r.generated_id}</td>
                <td>{r.event_title}</td>
                <td><span className={`badge ${r.kind === "approved" ? "supported" : "uncertain"}`}>{r.kind}</span></td>
                <td>{new Date(r.created_at).toLocaleString()}</td>
                <td><a className="btn small" href={api.downloadUrl(r.generated_id)} target="_blank" rel="noreferrer"
                  aria-label={`Download report ${r.generated_id} for ${r.event_title}`}>Download</a></td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </main>
  );
}
