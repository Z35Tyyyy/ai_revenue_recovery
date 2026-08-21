import React, { useState } from "react";
import { pct } from "./api.js";

function CaseCard({ c }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="case" onClick={() => setOpen((o) => !o)}>
      <div className="top">
        <span className="reason">{c.reason}</span>
        <span className="chip">{c.class}</span>
        <span className="meta">
          {c.amount} · {c.customer.city} · {c.customer.language}/{c.customer.channel}
        </span>
        <span className="spacer" />
        <span className="meta">P {pct(c.predicted_recover_prob)}</span>
        <span className={`status ${c.status}`}>{c.status}</span>
      </div>
      {open && (
        <div className="trace">
          {c.decision && (
            <div className="meta" style={{ marginBottom: 6 }}>
              <b style={{ color: "var(--text)" }}>Decision:</b> {c.decision.action}
              {c.decision.when ? ` @ ${new Date(c.decision.when).toLocaleString("en-IN")}` : ""}
            </div>
          )}
          <ul>
            {c.trace.map((t, i) => (
              <li key={i}>{t}</li>
            ))}
          </ul>
          <div className="acts">
            {c.actions.map((a, i) => (
              <span key={i} className={`act ${a.succeeded ? "ok" : "no"}`}>
                {a.type}
                {a.channel !== "none" ? ` · ${a.channel}` : ""}
                {a.succeeded ? " ✓" : ""}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default function CaseStream({ cases }) {
  return (
    <div className="stream">
      {cases.map((c) => (
        <CaseCard key={c.id} c={c} />
      ))}
    </div>
  );
}
