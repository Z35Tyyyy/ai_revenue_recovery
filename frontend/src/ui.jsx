import React from "react";
import { formatINR, pct } from "./api.js";

export function Card({ children, className = "" }) {
  return <div className={`card ${className}`}>{children}</div>;
}

export function Kpi({ value, label, sub, grad }) {
  return (
    <Card className="kpi">
      <div className={`v ${grad ? "grad" : ""}`}>{value}</div>
      <div className="l">{label}</div>
      {sub && <div className="s">{sub}</div>}
    </Card>
  );
}

const POLICY_LABELS = {
  no_action: "No recovery",
  fixed_retry: "Fixed retry (default)",
  generic_dunning: "Retry + generic email",
  engine: "AI Revenue Recovery",
};
const ORDER = ["no_action", "fixed_retry", "generic_dunning", "engine"];

export function PolicyBars({ policies }) {
  const max = Math.max(...ORDER.map((k) => policies[k]?.recovery_rate || 0), 0.01);
  return (
    <div className="bars">
      {ORDER.map((k) => {
        const p = policies[k];
        if (!p) return null;
        const eng = k === "engine";
        return (
          <div className="bar-row" key={k}>
            <div className={`name ${eng ? "eng" : ""}`}>{POLICY_LABELS[k]}</div>
            <div className="track">
              <div
                className={`fill ${eng ? "eng" : ""}`}
                style={{ width: `${(p.recovery_rate / max) * 100}%` }}
              />
            </div>
            <div className="val">{pct(p.recovery_rate)}</div>
          </div>
        );
      })}
    </div>
  );
}

export function PolicyTable({ policies }) {
  return (
    <table className="tbl">
      <thead>
        <tr>
          <th>Policy</th>
          <th className="num">Recovery</th>
          <th className="num">Revenue</th>
          <th className="num">Retries</th>
          <th className="num">Messages</th>
          <th className="num">Avg days</th>
        </tr>
      </thead>
      <tbody>
        {ORDER.map((k) => {
          const p = policies[k];
          if (!p) return null;
          return (
            <tr key={k} className={k === "engine" ? "eng" : ""}>
              <td>{POLICY_LABELS[k]}</td>
              <td className="num">{pct(p.recovery_rate)}</td>
              <td className="num">{formatINR(p.revenue_recovered_paise)}</td>
              <td className="num">{p.retries.toLocaleString("en-IN")}</td>
              <td className="num">{p.nudges.toLocaleString("en-IN")}</td>
              <td className="num">{p.avg_days_to_recover ?? "—"}</td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

export function ByClassBars({ engine, fixed }) {
  const classes = Object.keys(engine).sort((a, b) => engine[b] - engine[a]);
  return (
    <div>
      <div className="legend">
        <span><i className="dot" style={{ background: "#3395ff" }} /> Fixed retry</span>
        <span><i className="dot" style={{ background: "#22c58b" }} /> AI engine</span>
      </div>
      {classes.map((c) => (
        <div className="gbar" key={c}>
          <div className="cls">{c}</div>
          <div className="gtracks">
            <div className="gline">
              <div className="mini"><i className="fill-base" style={{ width: `${(fixed[c] || 0) * 100}%` }} /></div>
              <div className="val">{pct(fixed[c] || 0)}</div>
            </div>
            <div className="gline">
              <div className="mini"><i className="fill-eng" style={{ width: `${(engine[c] || 0) * 100}%` }} /></div>
              <div className="val">{pct(engine[c] || 0)}</div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

export function BanditTable({ bandit }) {
  const contexts = Object.keys(bandit).sort();
  return (
    <table className="tbl">
      <thead>
        <tr>
          <th>Failure class</th>
          <th>Learned best action (success rate)</th>
        </tr>
      </thead>
      <tbody>
        {contexts.map((ctx) => {
          const arms = bandit[ctx];
          const sorted = Object.entries(arms).sort((a, b) => b[1] - a[1]);
          return (
            <tr key={ctx}>
              <td>{ctx}</td>
              <td>
                {sorted.map(([arm, rate], i) => (
                  <span
                    key={arm}
                    className="chip"
                    style={{
                      marginRight: 6,
                      color: i === 0 ? "var(--good)" : "var(--muted)",
                      borderColor: i === 0 ? "rgba(34,197,139,.4)" : "var(--line)",
                    }}
                  >
                    {arm} · {pct(rate)}
                  </span>
                ))}
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
