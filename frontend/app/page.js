"use client";
import { useEffect, useState } from "react";
import { api } from "../lib/api";
import Logo from "./Logo";

const DEMO_CODE = process.env.NEXT_PUBLIC_DEMO_CODE || "schmitz2026";

export default function Page() {
  const [ok, setOk] = useState(false);
  useEffect(() => {
    try { if (sessionStorage.getItem("demo_ok") === "1") setOk(true); } catch {}
  }, []);
  if (!ok) return <Gate onOk={() => setOk(true)} />;
  return <Console onSignOut={() => { try { sessionStorage.removeItem("demo_ok"); } catch {}; setOk(false); }} />;
}

function Gate({ onOk }) {
  const [code, setCode] = useState("");
  const [err, setErr] = useState("");
  const submit = () => {
    if (code.trim() === DEMO_CODE) {
      try { sessionStorage.setItem("demo_ok", "1"); } catch {}
      onOk();
    } else setErr("Incorrect access key.");
  };
  return (
    <div className="gate">
      <div className="gate-card">
        <Logo size={48} />
        <h1>Evidence Console</h1>
        <p>Schmitz-Stiftungen · program reporting (exercise demo)</p>
        <input type="password" placeholder="Demo access key" value={code}
          onChange={(e) => setCode(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && submit()} autoFocus />
        <button className="btn" style={{ width: "100%" }} onClick={submit}>Enter</button>
        {err && <div className="gate-err">{err}</div>}
        <div className="gate-hint">Demo key: <b>{DEMO_CODE}</b></div>
      </div>
    </div>
  );
}

function Console({ onSignOut }) {
  const [view, setView] = useState("events"); // events | report | history
  const [eventId, setEventId] = useState(null);
  const [toast, setToast] = useState(null);
  const flash = (msg, err = false) => { setToast({ msg, err }); setTimeout(() => setToast(null), 2600); };

  return (
    <>
      <div className="utilitybar">
        <span className="tag">Exercise demo — not affiliated with the named organisation</span>
        <span>Evidence-based reporting</span>
      </div>
      <div className="header">
        <div className="brand">
          <Logo />
          <div className="word"><b>SCHMITZ-STIFTUNGEN</b><span>Evidence Console</span></div>
        </div>
        <div className="nav">
          <button className={view === "events" ? "active" : ""} onClick={() => setView("events")}>Events</button>
          <button className={view === "history" ? "active" : ""} onClick={() => setView("history")}>Report history</button>
        </div>
        <div className="spacer" />
        <button className="ghost" onClick={onSignOut}>Sign out</button>
      </div>

      {view === "events" && <Events onOpen={(id) => { setEventId(id); setView("report"); }} flash={flash} />}
      {view === "report" && eventId && <Report eventId={eventId} onBack={() => setView("events")} flash={flash} />}
      {view === "history" && <History flash={flash} />}

      {toast && <div className={`toast ${toast.err ? "err" : ""}`}>{toast.msg}</div>}
    </>
  );
}

function Events({ onOpen, flash }) {
  const [q, setQ] = useState("");
  const [rows, setRows] = useState(null);
  const [scenarios, setScenarios] = useState([]);
  const [busy, setBusy] = useState(false);

  const load = async (query = "") => {
    try { setRows(await api.events(query)); } catch (e) { flash("Load failed: " + e.message, true); setRows([]); }
  };
  useEffect(() => { load(); api.scenarios().then(setScenarios).catch(() => {}); }, []);

  const seed = async (sid) => {
    setBusy(true);
    try { const r = await api.loadScenario(sid); flash("Event created"); await load(q); onOpen(r.event_id); }
    catch (e) { flash("Could not create event: " + e.message, true); }
    finally { setBusy(false); }
  };

  return (
    <div className="wrap">
      <div className="pagehead">
        <h1>Program events</h1>
        <p>Each event holds the field reports received about it. Open one to build its evidence-based report.</p>
      </div>
      <div className="row" style={{ marginBottom: 16 }}>
        <div className="searchbar">
          <input placeholder="Search events by name…" value={q}
            onChange={(e) => { setQ(e.target.value); load(e.target.value); }} />
        </div>
        <button className="btn" disabled={busy || !scenarios.length}
          onClick={() => {
            const s = scenarios.find((x) => /schmitz|yds/i.test(x.context_id + x.scenario_id)) || scenarios[0];
            if (s) seed(s.scenario_id);
          }}>+ New event</button>
      </div>

      {rows === null && <div className="loading">Loading…</div>}
      {rows && rows.length === 0 && <div className="empty">No events yet. Use “+ New” to create one from a synthetic scenario.</div>}
      {rows && rows.map((e) => (
        <div key={e.event_id} className="card eventcard" onClick={() => onOpen(e.event_id)}>
          <div className="grow">
            <h3>{e.title}</h3>
            <div className="meta">{e.program} · {e.period} · {e.total_reports} report(s)</div>
          </div>
          <span className={`badge status-${e.report_status}`}>{e.report_status}</span>
          {e.needs_attention
            ? <span className="pill-attn">{e.new_reports} new · needs report</span>
            : <span className="pill-ok">up to date</span>}
        </div>
      ))}
    </div>
  );
}

function Report({ eventId, onBack, flash }) {
  const [rep, setRep] = useState(null);
  const [busy, setBusy] = useState("");
  const [revision, setRevision] = useState(null);
  const [instruction, setInstruction] = useState("");
  const [selClaim, setSelClaim] = useState(null);

  const refresh = async () => { try { setRep(await api.report(eventId)); } catch (e) { flash("Load failed: " + e.message, true); } };
  useEffect(() => { refresh(); }, [eventId]);

  const run = async (label, fn) => {
    setBusy(label);
    try { await fn(); await refresh(); }
    catch (e) { flash(label + " failed: " + e.message, true); }
    finally { setBusy(""); }
  };

  const doRevise = async () => {
    if (!instruction.trim()) return;
    setBusy("revise");
    try {
      const r = await api.revise(eventId, instruction.trim());
      setRevision(r.revision_id); setInstruction(""); await refresh();
      flash("Revision proposed — accept or refuse");
    } catch (e) { flash("Revise failed: " + e.message, true); }
    finally { setBusy(""); }
  };
  const decide = async (decision) => {
    setBusy("decide");
    try { await api.reviseDecision(revision, decision); setRevision(null); await refresh(); flash(`Revision ${decision}ed`); }
    catch (e) { flash("Failed: " + e.message, true); }
    finally { setBusy(""); }
  };

  if (!rep) return <div className="wrap"><div className="loading">Loading report…</div></div>;

  return (
    <div className="wrap">
      <button className="ghost" onClick={onBack} style={{ marginBottom: 14 }}>← All events</button>
      <div className="pagehead">
        <h1>{rep.title}</h1>
        <p>{rep.program} · {rep.period} &nbsp; <span className={`badge status-${rep.status}`}>{rep.status}</span></p>
      </div>

      <div className="row" style={{ marginBottom: 16 }}>
        <button className="btn" disabled={busy} onClick={() => run("Analyze", () => api.analyze(eventId))}>
          {busy === "Analyze" ? "Analyzing…" : rep.claims.length ? "Re-generate" : "Generate report"}</button>
        <button className="btn sec" disabled={busy || !rep.claims.length} onClick={() => run("Approve", () => api.approve(eventId))}>Approve → PDF</button>
      </div>

      {revision && (
        <div className="revise-banner">
          <h4>Revision proposed</h4>
          <p style={{ margin: "0 0 10px", fontSize: 14 }}>The agent re-generated the report and the PDF from your note. Keep it or revert.</p>
          <div className="row">
            <button className="btn small" disabled={busy} onClick={() => decide("accept")}>Accept</button>
            <button className="ghost" disabled={busy} onClick={() => decide("refuse")}>Refuse (revert)</button>
          </div>
        </div>
      )}

      {rep.claims.length === 0 && <div className="empty">No report yet. Click “Generate report”.</div>}

      {rep.claims.map((c) => (
        <div key={c.id} className={`claim ${selClaim === c.id ? "sel" : ""}`}>
          <span className={`badge ${c.status}`}>{c.status}</span>
          <div className="ctext">{c.text}</div>
          <div className="cmeta">
            {c.value && <span>value: {c.value}</span>}
            {c.unit && <span>unit: {c.unit}</span>}
            {c.period && <span>period: {c.period}</span>}
            <span>evidence:{" "}
              {c.evidence_ids.length ? c.evidence_ids.map((id) => (
                <span key={id} className="evchip" onClick={() => {
                  setSelClaim(c.id);
                  document.getElementById("ev-" + id)?.scrollIntoView({ behavior: "smooth", block: "center" });
                }}>#{id}</span>
              )) : <em>none</em>}
            </span>
          </div>
          <div className="why">why: {c.reasoning}</div>
        </div>
      ))}

      {/* revise via note */}
      {rep.claims.length > 0 && (
        <>
          <div className="section-title">Ask the agent to revise</div>
          <div className="card">
            <div className="noterow">
              <input placeholder='e.g. "sharper follow-up questions on the missing assessment"'
                value={instruction} onChange={(e) => setInstruction(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && doRevise()} />
              <button className="btn small" disabled={busy === "revise"} onClick={doRevise}>
                {busy === "revise" ? "Revising…" : "Submit note"}</button>
            </div>
          </div>
        </>
      )}

      {/* suggestions */}
      {rep.suggestions.length > 0 && (
        <>
          <div className="section-title">Open questions for the partner</div>
          <div className="card">
            {rep.suggestions.map((s) => (
              <div key={s.id} className="sugg">
                <span className="q">{s.question}</span>
                <span className={`st ${s.officer_validated}`}>{s.officer_validated}</span>
                {s.officer_validated === "pending" && (
                  <>
                    <button className="btn small" onClick={() => run("keep", () => api.suggestionDecision(s.id, "kept"))}>Keep</button>
                    <button className="ghost" style={{ padding: "4px 8px", fontSize: 12 }} onClick={() => run("dismiss", () => api.suggestionDecision(s.id, "dismissed"))}>Dismiss</button>
                  </>
                )}
              </div>
            ))}
          </div>
        </>
      )}

      {/* evidence appendix */}
      <div className="section-title">Evidence (verbatim source records)</div>
      <div className="card">
        {rep.evidence.map((e) => (
          <div key={e.id} className="evrec" id={"ev-" + e.id}>
            <div className="head">#{e.id} — {e.role} / {e.format}{e.simulated && <span className="sim">simulated</span>}</div>
            <div className="body">{e.excerpt}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

function History({ flash }) {
  const [q, setQ] = useState("");
  const [rows, setRows] = useState(null);
  const load = async (query = "") => { try { setRows(await api.history(query)); } catch (e) { flash("Load failed: " + e.message, true); setRows([]); } };
  useEffect(() => { load(); }, []);
  return (
    <div className="wrap">
      <div className="pagehead">
        <h1>Report history</h1>
        <p>Every report the agent generated. Search by event name and download the PDF.</p>
      </div>
      <div className="searchbar" style={{ marginBottom: 16, maxWidth: 420 }}>
        <input placeholder="Search by event name…" value={q}
          onChange={(e) => { setQ(e.target.value); load(e.target.value); }} />
      </div>
      {rows === null && <div className="loading">Loading…</div>}
      {rows && rows.length === 0 && <div className="empty">No generated reports yet.</div>}
      {rows && rows.length > 0 && (
        <table className="htable">
          <thead><tr><th>#</th><th>Event</th><th>Kind</th><th>Generated</th><th></th></tr></thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.generated_id}>
                <td>{r.generated_id}</td>
                <td>{r.event_title}</td>
                <td><span className={`badge ${r.kind === "approved" ? "supported" : "uncertain"}`}>{r.kind}</span></td>
                <td>{new Date(r.created_at).toLocaleString()}</td>
                <td><a className="btn small" href={api.downloadUrl(r.generated_id)} target="_blank" rel="noreferrer">Download</a></td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
