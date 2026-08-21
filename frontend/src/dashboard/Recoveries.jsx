import React, { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { api, pct } from "../api.js";
import { StatusPill } from "../components/primitives.jsx";
import { actionLabel, classLabel } from "../lib/labels.js";
import SAMPLE_CASES from "../lib/sampleCases.json";

const FILTERS = [
  { key: "all", label: "All" },
  { key: "recovered", label: "Recovered" },
  { key: "halted", label: "Halted" },
  { key: "gave_up", label: "Gave up" },
];

export function Recoveries() {
  const [cases, setCases] = useState([]);
  const [filter, setFilter] = useState("all");
  const [selected, setSelected] = useState(null);

  useEffect(() => {
    // Fall back to a baked sample so the page renders in the static preview / offline.
    api.cases({ limit: 80 })
      .then((r) => setCases(r.cases))
      .catch(() => setCases(SAMPLE_CASES));
  }, []);

  const rows = filter === "all" ? cases : cases.filter((c) => c.status === filter);

  return (
    <div>
      <div className="page-h">
        <h1>Recoveries</h1>
        <p>Every failed charge the agent worked — click a row for its reasoning.</p>
      </div>

      <div className="rec-toolbar">
        {FILTERS.map((f) => (
          <button
            key={f.key}
            className={`filter-chip ${filter === f.key ? "active" : ""}`}
            onClick={() => setFilter(f.key)}
          >
            {f.label}
          </button>
        ))}
      </div>

      <div className="rec-list">
          <div className="rec-head">
            <span>Failure</span>
            <span>Amount</span>
            <span className="r-hide">Customer</span>
            <span className="r-hide">Agent action</span>
            <span className="r-hide">P</span>
            <span>Status</span>
          </div>
          {rows.map((c) => (
            <div className="rec-row" key={c.id} onClick={() => setSelected(c)}>
              <div>
                <div className="r-reason">{c.reason}</div>
                <div className="r-sub">{classLabel(c.class)}</div>
              </div>
              <div className="r-amt">{c.amount}</div>
              <div className="r-cell r-hide">{c.customer.city} · {c.customer.language}/{c.customer.channel}</div>
              <div className="r-cell r-hide">{c.decision ? actionLabel(c.decision.action) : "—"}</div>
              <div className="r-prob r-hide">{pct(c.predicted_recover_prob)}</div>
              <div><StatusPill status={c.status} /></div>
            </div>
          ))}
        </div>

      <AnimatePresence>
        {selected && <Drawer c={selected} onClose={() => setSelected(null)} />}
      </AnimatePresence>
    </div>
  );
}

function Drawer({ c, onClose }) {
  const nudge = c.actions.find((a) => a.message);
  const link = c.actions.find((a) => a.payment_link)?.payment_link;
  return (
    <>
      <motion.div
        className="drawer-overlay"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={onClose}
      />
      <motion.aside
        className="drawer"
        initial={{ x: "100%" }}
        animate={{ x: 0 }}
        exit={{ x: "100%" }}
        transition={{ type: "spring", damping: 30, stiffness: 300 }}
      >
        <div className="drawer-head">
          <div>
            <div className="row" style={{ gap: 10 }}>
              <span className="h3">{c.reason}</span>
              <StatusPill status={c.status} />
            </div>
            <div className="small" style={{ marginTop: 4 }}>
              {c.amount} · {classLabel(c.class)} · {c.customer.city} · {c.customer.language}/{c.customer.channel}
            </div>
          </div>
          <button className="drawer-close" onClick={onClose}>✕</button>
        </div>
        <div className="drawer-body">
          {c.decision && (
            <div className="d-sec">
              <div className="d-k">Decision</div>
              <div className="row between">
                <span className="h3" style={{ fontSize: "1.05rem" }}>{actionLabel(c.decision.action)}</span>
                <span className="chip accent mono">{c.decision.action}</span>
              </div>
            </div>
          )}

          <div className="d-sec">
            <div className="d-k">Reasoning trace</div>
            <div className="trace-list">
              {c.trace.map((t, i) => (
                <div className="trace-item" key={i}>
                  <span className="ti">{String(i + 1).padStart(2, "0")}</span>
                  <span>{t}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="d-sec">
            <div className="d-k">Actions taken</div>
            <div className="row wrap" style={{ gap: 6 }}>
              {c.actions.length === 0 && <span className="small">None — the agent stopped.</span>}
              {c.actions.map((a, i) => (
                <span key={i} className={`chip ${a.succeeded ? "good" : ""} mono`}>
                  {a.type}{a.channel !== "none" ? ` · ${a.channel}` : ""}{a.succeeded ? " ✓" : ""}
                </span>
              ))}
            </div>
          </div>

          {nudge?.message && (
            <div className="d-sec">
              <div className="d-k">Dunning message</div>
              <div className="msg-box">
                <div className="msg-meta">via {nudge.channel} · authored by {nudge.authored_by || "template"}</div>
                {nudge.message}
              </div>
            </div>
          )}

          {link && (
            <div className="d-sec">
              <div className="d-k">Payment link</div>
              <div className="link-box">{link}</div>
            </div>
          )}
        </div>
      </motion.aside>
    </>
  );
}
