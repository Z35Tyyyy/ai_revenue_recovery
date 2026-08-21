import React, { useEffect, useState } from "react";
import { api, formatINR, pct } from "./api.js";
import { Card, Kpi, PolicyBars, PolicyTable, ByClassBars, BanditTable } from "./ui.jsx";
import CaseStream from "./CaseStream.jsx";
import TryIt from "./TryIt.jsx";

export default function App() {
  const [metrics, setMetrics] = useState(null);
  const [cases, setCases] = useState([]);
  const [reasons, setReasons] = useState([]);
  const [health, setHealth] = useState(null);
  const [err, setErr] = useState(null);

  useEffect(() => {
    Promise.all([api.metrics(), api.cases({ limit: 40 }), api.reasons(), api.health()])
      .then(([m, c, r, h]) => {
        setMetrics(m);
        setCases(c.cases);
        setReasons(r.reasons);
        setHealth(h);
      })
      .catch((e) => setErr(String(e)));
  }, []);

  if (err)
    return (
      <div className="wrap">
        <div className="loading">
          Could not reach the API — start it with <code>make api</code>.<br />
          <span style={{ fontSize: 12 }}>{err}</span>
        </div>
      </div>
    );
  if (!metrics) return <div className="wrap"><div className="loading">Loading engine metrics…</div></div>;

  const holdout = metrics.holdout;
  const policies = holdout ? holdout.policies : null;
  const eng = policies?.engine;
  const fixed = policies?.fixed_retry;
  const uplift = holdout?.uplift?.vs_fixed_retry;
  const auc = holdout?.engine_prediction_auc;
  const bandit = holdout?.bandit || metrics.bandit;
  const cap = metrics.capabilities;

  return (
    <div className="wrap">
      <header className="hd">
        <div className="brand">
          <div className="logo">♻️</div>
          <div>
            <h1>AI Revenue Recovery</h1>
            <p>Agentic recovery of failed recurring payments · Razorpay Buildathon Track 3</p>
          </div>
        </div>
        <div className="badges">
          <span className={`badge ${cap.razorpay_live ? "on" : "off"}`}>
            {cap.razorpay_live ? "Razorpay: live test-mode" : "Razorpay: mock"}
          </span>
          <span className={`badge ${cap.llm_enabled ? "on" : "off"}`}>
            {cap.llm_enabled ? `Dunning: ${cap.llm_provider}` : "Dunning: templates"}
          </span>
          {health && <span className="badge on">{health.sample_cases} episodes warmed</span>}
        </div>
      </header>

      {eng && (
        <div className="section">
          <div className="grid cols-4">
            <Kpi grad value={pct(eng.recovery_rate)} label="Recovery rate (held-out)"
              sub={uplift ? `+${(uplift.recovery_rate_abs * 100).toFixed(1)} pts vs default` : null} />
            <Kpi grad value={uplift ? `+${(uplift.recovery_rate_rel * 100).toFixed(0)}%` : "—"}
              label="Relative uplift vs fixed retry"
              sub={uplift ? `+${formatINR(uplift.revenue_recovered_delta_paise)} recovered` : null} />
            <Kpi value={formatINR(eng.revenue_recovered_paise)} label="Revenue recovered (holdout)"
              sub={`of ${formatINR(eng.revenue_total_paise)} at risk`} />
            <Kpi value={auc ? auc.toFixed(3) : "—"} label="Triage prediction AUC"
              sub={`${eng.retries.toLocaleString("en-IN")} retries · ${eng.nudges.toLocaleString("en-IN")} msgs`} />
          </div>
        </div>
      )}

      {policies && (
        <div className="section">
          <h2>Recovery rate by policy <span>· same hidden ground truth, unseen holdout</span></h2>
          <div className="grid cols-2">
            <Card><PolicyBars policies={policies} /></Card>
            <Card><PolicyTable policies={policies} /></Card>
          </div>
        </div>
      )}

      {eng && fixed && (
        <div className="section">
          <h2>Recovery by failure class <span>· where the intelligence pays off</span></h2>
          <Card><ByClassBars engine={eng.by_class_rate} fixed={fixed.by_class_rate} /></Card>
        </div>
      )}

      <div className="section">
        <h2>Try the agent <span>· diagnose a failed charge and generate a recovery</span></h2>
        <TryIt reasons={reasons} />
      </div>

      {bandit && Object.keys(bandit).length > 0 && (
        <div className="section">
          <h2>What the bandit learned <span>· best action per failure class, from live outcomes</span></h2>
          <Card><BanditTable bandit={bandit} /></Card>
        </div>
      )}

      <div className="section">
        <h2>Live recovery stream <span>· click a case for the agent's reasoning trace</span></h2>
        <CaseStream cases={cases} />
      </div>

      <div className="foot">
        Simulation-first · credential-optional · built for the Razorpay AI Buildathon 2026.
      </div>
    </div>
  );
}
