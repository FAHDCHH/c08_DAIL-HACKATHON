"use client";
import { useEffect, useState } from "react";
import Logo from "./Logo";
import Gate from "./components/Gate";
import Events from "./components/Events";
import Report from "./components/Report";
import History from "./components/History";
import { Toast } from "./components/ui";

export default function Page() {
  const [ok, setOk] = useState(false);
  useEffect(() => {
    try { if (sessionStorage.getItem("demo_ok") === "1") setOk(true); } catch {}
  }, []);
  if (!ok) return <Gate onOk={() => setOk(true)} />;
  return <Console onSignOut={() => { try { sessionStorage.removeItem("demo_ok"); } catch {}; setOk(false); }} />;
}

function Console({ onSignOut }) {
  const [view, setView] = useState("events");
  const [eventId, setEventId] = useState(null);
  const [toast, setToast] = useState(null);
  const flash = (msg, err = false) => { setToast({ msg, err }); setTimeout(() => setToast(null), 2600); };

  const open = (id) => { setEventId(id); setView("report"); };

  return (
    <>
      <div className="utilitybar">
        <span className="tag">Exercise demo — not affiliated with the named organisation</span>
        <span>Evidence-based reporting</span>
      </div>

      <header className="header">
        <div className="brand">
          <Logo />
          <div className="word"><b>SCHMITZ-STIFTUNGEN</b><span>Evidence Console</span></div>
        </div>
        <nav className="nav" aria-label="Primary">
          <button className={view === "events" || view === "report" ? "active" : ""} onClick={() => setView("events")}
            aria-current={view === "events" || view === "report" ? "page" : undefined}>Events</button>
          <button className={view === "history" ? "active" : ""} onClick={() => setView("history")}
            aria-current={view === "history" ? "page" : undefined}>Report history</button>
        </nav>
        <div className="spacer" />
        <button className="ghost" onClick={onSignOut}>Sign out</button>
      </header>

      {view === "events" && <Events onOpen={open} />}
      {view === "report" && eventId && <Report eventId={eventId} onBack={() => setView("events")} flash={flash} />}
      {view === "history" && <History flash={flash} />}

      <Toast toast={toast} />
    </>
  );
}
