"use client";
import { useState } from "react";
import Logo from "../Logo";

const DEMO_CODE = process.env.NEXT_PUBLIC_DEMO_CODE || "schmitz2026";

export default function Gate({ onOk }) {
  const [code, setCode] = useState("");
  const [err, setErr] = useState("");

  const submit = (e) => {
    e?.preventDefault();
    if (code.trim() === DEMO_CODE) {
      try { sessionStorage.setItem("demo_ok", "1"); } catch {}
      onOk();
    } else {
      setErr("Incorrect access key.");
    }
  };

  return (
    <main className="gate">
      <form className="gate-card" onSubmit={submit}>
        <Logo size={48} />
        <h1>Evidence Console</h1>
        <p>Schmitz-Stiftungen · program reporting (exercise demo)</p>
        <label htmlFor="demo-key" className="sr-only">Demo access key</label>
        <input id="demo-key" type="password" placeholder="Demo access key" value={code}
          autoFocus autoComplete="off"
          aria-invalid={err ? "true" : "false"}
          aria-describedby={err ? "gate-err" : undefined}
          onChange={(e) => { setCode(e.target.value); setErr(""); }} />
        <button className="btn" style={{ width: "100%" }} type="submit">Enter</button>
        {err && <div id="gate-err" className="gate-err" role="alert">{err}</div>}
        <p className="gate-hint">Demo key: <b>{DEMO_CODE}</b></p>
      </form>
    </main>
  );
}
