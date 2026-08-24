import React from "react";
import { Link } from "react-router-dom";
import { Icon } from "../components/ui.jsx";
import { useRiskOverview } from "../lib/useData.js";
import { formatINR } from "../api.js";

// "One agent, many sources." Revenue loss spans the whole funnel — a payment
// degrades, a checkout is abandoned, an invoice goes overdue. The same detect →
// decide → bounded-execute agent handles each; this section proves it clears the
// Track-3 bar on all three: measured money recovered, compliant escalation, a
// stopping rule, and an audit trail.

const NEW_SOURCES = ["checkout_abandonment", "overdue_receivable"];

export function FunnelOverview() {
  const ov = useRiskOverview();
  if (!ov?.sources?.length) return null;

  const auditFor = (key) => (ov.batches?.[key]?.audit || []).find((a) => a.trace?.length);

  return (
    <section className="funnel">
      <div className="panel__head panel__head--loose">
        <h2>Revenue at risk · across the funnel</h2>
        <span className="panel__legend mono">one agent · three sources</span>
      </div>

      <p className="funnel__lead">
        Revenue loss is never one clean step — a payment degrades, a checkout is abandoned, an
        invoice goes overdue. The <strong>same agent</strong> detects the risk, determines the right
        intervention, and runs a <strong>bounded</strong> recovery workflow — measured on each.
        Recovered <strong>{formatINR(ov.total_recovered_paise)}</strong> of{" "}
        <strong>{formatINR(ov.total_at_risk_paise)}</strong> at risk across all three.
      </p>

      <div className="funnel__cards">
        {ov.sources.map((s) => (
          <div
            key={s.source}
            className={`funnel__card ${s.source === "payment_failure" ? "funnel__card--lead" : ""}`}
          >
            <div className="funnel__card-label">{s.label}</div>
            <div className="funnel__card-val tnum">{formatINR(s.recovered_paise)}</div>
            <div className="funnel__card-sub">of {formatINR(s.at_risk_paise)} at risk</div>
            <div className="funnel__card-foot">
              {s.uplift_pts != null && (
                <span className="funnel__uplift">+{s.uplift_pts} pts vs generic</span>
              )}
              <span className="funnel__measured mono">{s.measured}</span>
            </div>
          </div>
        ))}
      </div>

      {/* the bar, met on the new sources too: escalation → stopping rule → audit trail */}
      <div className="funnel__audits">
        {NEW_SOURCES.map((key) => {
          const b = ov.batches?.[key];
          const a = auditFor(key);
          if (!b || !a) return null;
          return (
            <div key={key} className="funnel__audit card">
              <div className="funnel__audit-head">
                <span className="funnel__audit-title">
                  <Icon name="bolt" size={13} /> {b.label} — one case, audited
                </span>
                <span className={`funnel__audit-tag ${a.recovered ? "is-won" : "is-stop"}`}>
                  {a.recovered ? "recovered" : "stopped"} · {a.amount}
                </span>
              </div>
              <ol className="funnel__trace">
                {a.trace.map((t, i) => (
                  <li key={i}>
                    <span className="funnel__trace-n mono">{String(i + 1).padStart(2, "0")}</span>
                    <span>{t}</span>
                  </li>
                ))}
              </ol>
            </div>
          );
        })}
      </div>

      <p className="funnel__note mono">
        Payment failures carry the trained models + held-out eval; checkout &amp; receivables run the
        same detect→decide→bounded-execute agent on their own measured batches, calibrated to public
        benchmarks. Every decision is logged — see the <Link to="/dashboard/agent">Agent</Link> to run one.
      </p>
    </section>
  );
}
