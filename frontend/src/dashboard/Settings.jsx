import React from "react";
import { Card } from "../components/primitives.jsx";
import { useHealth, useMetrics } from "../lib/useData.js";

function Row({ k, v }) {
  return (
    <div className="set-row card">
      <span className="sk">{k}</span>
      <span className="sv">{v}</span>
    </div>
  );
}

export function Settings() {
  const health = useHealth();
  const { metrics } = useMetrics();
  const h = metrics?.holdout;
  const hd = h?.holdout;

  return (
    <div>
      <div className="page-h">
        <h1>Settings</h1>
        <p>Engine capabilities and evaluation configuration.</p>
      </div>

      <div className="section-title">Capabilities</div>
      <div className="set-grid">
        <Row k="Razorpay" v={health?.razorpay_live ? "live test-mode" : "mock gateway"} />
        <Row k="Dunning engine" v={health?.llm_enabled ? health.llm_provider : "templates"} />
        <Row k="Models" v={health?.models_loaded ? "loaded" : "—"} />
        <Row k="Warmed episodes" v={health?.sample_cases ?? "—"} />
      </div>

      <div className="section-title" style={{ marginTop: 26 }}>Evaluation</div>
      <div className="set-grid">
        <Row k="Held-out eval" v={health?.has_holdout_eval ? "present" : "not run"} />
        <Row k="Triage AUC" v={h ? h.engine_prediction_auc?.toFixed(3) : "—"} />
        <Row k="Holdout size" v={hd ? `${hd.customers?.toLocaleString("en-IN")} cust · ${hd.failures?.toLocaleString("en-IN")} fails` : "—"} />
        <Row k="Holdout seed" v={hd?.seed ?? "—"} />
      </div>

      <div className="soon" style={{ marginTop: 26, textAlign: "left", padding: "20px 22px" }}>
        <div className="sd" style={{ margin: 0, maxWidth: "none" }}>
          Configure providers in <span className="mono">.env</span> — <span className="mono">LLM_PROVIDER</span>{" "}
          (anthropic / groq / openai) and <span className="mono">RAZORPAY_KEY_ID</span> for live test-mode links.
          The evaluation always uses templates, so a key never changes the measured numbers.
        </div>
      </div>
    </div>
  );
}
