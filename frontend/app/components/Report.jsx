"use client";
import { useEffect, useState } from "react";
import { api } from "../../lib/api";
import { ErrorState, Skeleton, StatusBadge } from "./ui";

export default function Report({ eventId, onBack, flash }) {
  const [rep, setRep] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState("");
  const [revision, setRevision] = useState(null);
  const [instruction, setInstruction] = useState("");
  const [selClaim, setSelClaim] = useState(null);

  const refresh = async () => {
    setError(null);
    try { setRep(await api.report(eventId)); } catch (e) { setError(e.message); }
  };
  useEffect(() => { refresh(); }, [eventId]);

  const run = async (label, fn) => {
    setBusy(label);
    try { await fn(); await refresh(); }
    catch (e) { flash(label + " failed: " + e.message, true); }
    finally { setBusy(""); }
  };

  const doRevise = async (e) => {
    e?.preventDefault();
    if (!instruction.trim()) return;
    setBusy("revise");
    try {
      const r = await api.revise(eventId, instruction.trim());
      setRevision(r.revision_id); setInstruction(""); await refresh();
      flash("Revision proposed — accept or refuse");
    } catch (err) { flash("Revise failed: " + err.message, true); }
    finally { setBusy(""); }
  };
  const decide = async (decision) => {
    setBusy("decide");
    try { await api.reviseDecision(revision, decision); setRevision(null); await refresh(); flash(`Revision ${decision}ed`); }
    catch (e) { flash("Failed: " + e.message, true); }
    finally { setBusy(""); }
  };

  const jumpToEvidence = (id, claimId) => {
    setSelClaim(claimId);
    document.getElementById("ev-" + id)?.scrollIntoView({ behavior: "smooth", block: "center" });
  };

  return (
    <main className="wrap">
      <button className="ghost" onClick={onBack} style={{ marginBottom: 16 }}>← All events</button>

      {!rep && !error && <Skeleton lines={4} />}
      {error && <ErrorState message={"Could not load report: " + error} onRetry={refresh} />}

      {rep && (
        <>
          <header className="pagehead">
            <span className="eyebrow">Evidence-based report</span>
            <h1>{rep.title}</h1>
            <p>{rep.program} · {rep.period} &nbsp; <StatusBadge status={rep.status} kind="status" /></p>
          </header>

          <div className="row" style={{ marginBottom: 18 }}>
            <button className="btn" disabled={busy} onClick={() => run("Analyze", () => api.analyze(eventId))}>
              {busy === "Analyze" ? "Analyzing…" : rep.claims.length ? "Re-generate" : "Generate report"}</button>
            <button className="btn sec" disabled={busy || !rep.claims.length} onClick={() => run("Approve", () => api.approve(eventId))}>Approve → PDF</button>
          </div>

          {revision && (
            <div className="revise-banner" role="status">
              <h4>Revision proposed</h4>
              <p style={{ margin: "0 0 10px", fontSize: 14 }}>The agent re-generated the report and PDF from your note. Keep it or revert.</p>
              <div className="row">
                <button className="btn small" disabled={busy} onClick={() => decide("accept")}>Accept</button>
                <button className="ghost" disabled={busy} onClick={() => decide("refuse")}>Refuse (revert)</button>
              </div>
            </div>
          )}

          {rep.claims.length === 0 && (
            <div className="empty" role="status">
              <h3 className="empty-title">No report yet</h3>
              <p className="empty-hint">Generate the report to turn the source records into evidence-backed claims.</p>
            </div>
          )}

          {rep.claims.length > 0 && (
            <section aria-label="Claims">
              <ul className="u-list">
                {rep.claims.map((c, i) => (
                  <li key={c.id}>
                    <ClaimCard claim={c} selected={selClaim === c.id} index={i} onJump={jumpToEvidence} />
                  </li>
                ))}
              </ul>
            </section>
          )}

          {rep.claims.length > 0 && (
            <section aria-labelledby="revise-h">
              <h2 id="revise-h" className="section-title">Ask the agent to revise</h2>
              <form className="card" onSubmit={doRevise}>
                <div className="noterow">
                  <label htmlFor="revise-note" className="sr-only">Revision instruction</label>
                  <input id="revise-note" placeholder='e.g. "sharper follow-up questions on the missing assessment"'
                    value={instruction} onChange={(e) => setInstruction(e.target.value)} />
                  <button className="btn small" type="submit" disabled={busy === "revise"}>
                    {busy === "revise" ? "Revising…" : "Submit note"}</button>
                </div>
              </form>
            </section>
          )}

          {rep.suggestions.length > 0 && (
            <section aria-labelledby="oq-h">
              <h2 id="oq-h" className="section-title">Open questions for the partner</h2>
              <div className="card">
                <ul className="u-list">
                  {rep.suggestions.map((s) => (
                    <li key={s.id} className="sugg">
                      <span className="q">{s.question}</span>
                      <span className={`st ${s.officer_validated}`}>{s.officer_validated}</span>
                      {s.officer_validated === "pending" && (
                        <>
                          <button className="btn small" onClick={() => run("keep", () => api.suggestionDecision(s.id, "kept"))}>Keep</button>
                          <button className="ghost" style={{ padding: "4px 10px", fontSize: 12 }} onClick={() => run("dismiss", () => api.suggestionDecision(s.id, "dismissed"))}>Dismiss</button>
                        </>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            </section>
          )}

          <section aria-labelledby="ev-h">
            <h2 id="ev-h" className="section-title">Evidence (verbatim source records)</h2>
            <div className="card">
              {rep.evidence.map((e) => (
                <article key={e.id} className="evrec" id={"ev-" + e.id}>
                  <div className="head">#{e.id} — {e.role} / {e.format}{e.simulated && <span className="sim">simulated</span>}</div>
                  <div className="body">{e.excerpt}</div>
                </article>
              ))}
            </div>
          </section>
        </>
      )}
    </main>
  );
}

function ClaimCard({ claim, selected, index, onJump }) {
  return (
    <article className={`claim status-${claim.status} ${selected ? "sel" : ""}`}
      style={{ animationDelay: `${Math.min(index * 60, 400)}ms` }}>
      <StatusBadge status={claim.status} />
      <div className="ctext">{claim.text}</div>
      <div className="cmeta">
        {claim.value && <span>value: {claim.value}</span>}
        {claim.unit && <span>unit: {claim.unit}</span>}
        {claim.period && <span>period: {claim.period}</span>}
        <span>evidence:{" "}
          {claim.evidence_ids.length ? claim.evidence_ids.map((id) => (
            <button key={id} className="evchip" onClick={() => onJump(id, claim.id)}
              aria-label={`Jump to evidence record ${id}`}>#{id}</button>
          )) : <em>none</em>}
        </span>
      </div>
      <div className="why">why: {claim.reasoning}</div>
    </article>
  );
}
