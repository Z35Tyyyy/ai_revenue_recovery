import React from "react";
import { motion } from "framer-motion";
import { Card } from "../components/primitives.jsx";
import { formatINR } from "../api.js";
import { POLICY_LABEL, POLICY_ORDER } from "../lib/labels.js";
import { useMetrics } from "../lib/useData.js";

export function Experiments() {
  const { metrics } = useMetrics();
  if (!metrics) return <div className="soon">Loading…</div>;
  const p = metrics.holdout.policies;
  const max = Math.max(...POLICY_ORDER.map((k) => p[k]?.recovery_rate || 0), 0.01);

  return (
    <div>
      <div className="page-h">
        <h1>Experiments</h1>
        <p>Every policy run against identical hidden ground truth — so the gap is real skill.</p>
      </div>

      <Card>
        <div className="d-k" style={{ marginBottom: 16 }}>Recovery rate</div>
        <div className="exp-rows">
          {POLICY_ORDER.map((k, i) => {
            const pol = p[k];
            if (!pol) return null;
            const win = k === "engine";
            return (
              <div className={`exp-row ${win ? "win" : ""}`} key={k}>
                <span className="en">{POLICY_LABEL[k]}</span>
                <div className="et bar-track">
                  <motion.div
                    className={`bar-fill ${win ? "fill-green" : k === "no_action" ? "fill-muted" : "fill-blue"}`}
                    initial={{ width: 0 }}
                    animate={{ width: `${(pol.recovery_rate / max) * 100}%` }}
                    transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1], delay: i * 0.08 }}
                  />
                </div>
                <span className="ev">{(pol.recovery_rate * 100).toFixed(1)}%</span>
              </div>
            );
          })}
        </div>
      </Card>

      <div style={{ marginTop: 20, overflowX: "auto" }}>
        <Card pad={false}>
          <table className="metrics-table">
            <thead>
              <tr>
                <th>Policy</th>
                <th>Recovery</th>
                <th>Revenue recovered</th>
                <th>Retries</th>
                <th>Messages</th>
                <th>Avg days</th>
              </tr>
            </thead>
            <tbody>
              {POLICY_ORDER.map((k) => {
                const pol = p[k];
                if (!pol) return null;
                return (
                  <tr key={k} className={k === "engine" ? "win" : ""}>
                    <td>{POLICY_LABEL[k]}</td>
                    <td>{(pol.recovery_rate * 100).toFixed(1)}%</td>
                    <td>{formatINR(pol.revenue_recovered_paise)}</td>
                    <td>{(pol.retries || 0).toLocaleString("en-IN")}</td>
                    <td>{(pol.nudges || 0).toLocaleString("en-IN")}</td>
                    <td>{pol.avg_days_to_recover ?? "—"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </Card>
      </div>
    </div>
  );
}
