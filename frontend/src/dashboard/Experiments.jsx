import React from "react";
import { Card, Pill, Meter, Icon } from "../components/ui.jsx";
import { useMetrics } from "../lib/useData.js";
import { formatINR } from "../api.js";
import { POLICY_ORDER, POLICY_LABEL, classLabel } from "../lib/labels.js";

const CLASS_ORDER = [
  "needs_card_update", "needs_reauth", "insufficient_funds",
  "soft_decline", "transient", "hard_decline",
];

export function Experiments() {
  const { metrics, loading } = useMetrics();
  const P = metrics?.holdout?.policies || {};
  if (loading) return <div className="dash__loading mono">loading experiment…</div>;

  const maxRate = Math.max(...POLICY_ORDER.map((p) => P[p]?.recovery_rate || 0), 0.01);
  const rrate = (d) =>
    d?.revenue_total_paise ? d.revenue_recovered_paise / d.revenue_total_paise : 0;

  const ope = metrics?.holdout?.offpolicy;
  const opeRows = ope
    ? [
        { k: "Random logging policy", v: ope.logging_policy_value, tone: "neutral" },
        { k: "Direct Method (DM)", v: ope.estimates.direct_method, tone: "cool" },
        { k: "Inverse Propensity (IPS)", v: ope.estimates.ips, tone: "cool" },
        { k: "Self-normalized IPS", v: ope.estimates.snips, tone: "cool" },
        { k: "Doubly-Robust (DR)", v: ope.estimates.doubly_robust, tone: "pos", strong: true },
        { k: "Engine on-policy (truth)", v: ope.engine_onpolicy_value, tone: "pos", strong: true },
      ]
    : [];
  const opeMax = ope ? Math.max(...opeRows.map((r) => r.v), 0.01) : 1;

  return (
    <div className="page">
      <p className="page__lead">
        Four policies, one frozen holdout, identical hidden ground truth. Every difference below is
        attributable to the decision policy — not luck.
      </p>

      <Card className="xtable">
        <div className="xtable__scroll">
          <table className="xt">
            <thead>
              <tr>
                <th>Policy</th>
                <th className="xt__bar">Recovery rate</th>
                <th className="xt__num">Rate</th>
                <th className="xt__num">Revenue</th>
                <th className="xt__num">₹-rate</th>
                <th className="xt__num">Retries</th>
                <th className="xt__num">Msgs</th>
                <th className="xt__num">Days</th>
              </tr>
            </thead>
            <tbody>
              {POLICY_ORDER.map((p) => {
                const d = P[p];
                if (!d) return null;
                const win = p === "engine";
                return (
                  <tr key={p} className={win ? "xt__win" : ""}>
                    <td className="xt__name">
                      {POLICY_LABEL[p]} {win && <Icon name="bolt" size={12} />}
                    </td>
                    <td className="xt__bar">
                      <Meter value={d.recovery_rate / maxRate} tone={win ? "pos" : "neutral"} height={8} />
                    </td>
                    <td className={`xt__num ${win ? "xt__num--pos" : ""}`}>{(d.recovery_rate * 100).toFixed(1)}%</td>
                    <td className="xt__num">{formatINR(d.revenue_recovered_paise)}</td>
                    <td className="xt__num">{(rrate(d) * 100).toFixed(1)}%</td>
                    <td className="xt__num">{d.retries.toLocaleString("en-IN")}</td>
                    <td className="xt__num">{(d.nudges || 0).toLocaleString("en-IN")}</td>
                    <td className="xt__num">{d.avg_days_to_recover?.toFixed(1) ?? "—"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Card>

      <div className="panel__head panel__head--loose">
        <h2>Recovery rate by class · all policies</h2>
        <span className="panel__legend">
          {POLICY_ORDER.filter((p) => p !== "no_action").map((p) => (
            <span key={p} className="legend-item">
              <span className={`dot dot--${p === "engine" ? "pos" : p === "generic_dunning" ? "cool" : "muted"}`} />
              {POLICY_LABEL[p]}
            </span>
          ))}
        </span>
      </div>

      <div className="xclasses">
        {CLASS_ORDER.map((c) => (
          <Card key={c} className="xclass">
            <div className="xclass__name">{classLabel(c)}</div>
            {["fixed_retry", "generic_dunning", "engine"].map((p) => {
              const v = P[p]?.by_class_rate?.[c] ?? 0;
              const tone = p === "engine" ? "pos" : p === "generic_dunning" ? "cool" : "neutral";
              return (
                <div key={p} className="xclass__row">
                  <Meter value={v} tone={tone} height={5} />
                  <span className="xclass__pct tnum">{(v * 100).toFixed(0)}%</span>
                </div>
              );
            })}
          </Card>
        ))}
      </div>

      {ope && (
        <>
          <div className="panel__head panel__head--loose">
            <h2>Off-policy evaluation · counterfactual proof</h2>
            <span className="panel__legend mono">from logged data · n={ope.n?.toLocaleString("en-IN")}</span>
          </div>
          <Card className="panel">
            <p className="ope__lead">
              We estimate the engine&rsquo;s value from a <strong>random logging policy&rsquo;s</strong>{" "}
              data — never running the engine — the way Adyen &amp; Stripe validate a policy before an
              A/B test. The estimators track the on-policy truth, and all sit far above the random
              baseline.
            </p>
            <div className="ope">
              {opeRows.map((r) => (
                <div key={r.k} className={`ope__row ${r.strong ? "ope__row--strong" : ""}`}>
                  <span className="ope__name">{r.k}</span>
                  <span className="ope__meter">
                    <Meter value={r.v / opeMax} tone={r.tone} height={7} />
                  </span>
                  <span className="ope__pct tnum">{(r.v * 100).toFixed(1)}%</span>
                </div>
              ))}
            </div>
          </Card>
        </>
      )}
    </div>
  );
}
