import React from "react";
import { motion } from "framer-motion";
import { Card } from "../components/primitives.jsx";
import { Counter } from "../components/Counter.jsx";
import { Bar } from "../components/Bar.jsx";
import { formatINR } from "../api.js";
import { classLabel } from "../lib/labels.js";
import { useMetrics } from "../lib/useData.js";

function Funnel({ eng, fixed }) {
  const N = eng.total || 9000;
  const R = eng.recovered ?? Math.round(eng.recovery_rate * N);
  const stages = [
    { label: "Failed payments", count: N, w: 1, seg: "seg-total", val: `${N.toLocaleString("en-IN")}` },
    { label: "Diagnosed & triaged", count: N, w: 1, seg: "seg-total", val: "100%" },
    { label: "Action selected", count: N, w: 1, seg: "seg-base", val: "100%" },
  ];
  return (
    <div className="funnel">
      {stages.map((s, i) => (
        <div className="fstage" key={s.label}>
          <div className="fl">{s.label}</div>
          <div className="fbar">
            <motion.div
              className={`fill ${s.seg}`}
              initial={{ width: 0 }}
              animate={{ width: `${s.w * 100}%` }}
              transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1], delay: i * 0.08 }}
            />
            <span className="val">{s.val}</span>
          </div>
        </div>
      ))}
      <div className="fstage">
        <div className="fl">
          Recovered
          <span className="fc">{R.toLocaleString("en-IN")} of {N.toLocaleString("en-IN")}</span>
        </div>
        <div className="fbar">
          <motion.div
            className="fill seg-green"
            initial={{ width: 0 }}
            animate={{ width: `${eng.recovery_rate * 100}%` }}
            transition={{ duration: 0.9, ease: [0.22, 1, 0.36, 1], delay: 0.3 }}
          />
          <motion.div
            className="fill seg-base"
            initial={{ width: 0 }}
            animate={{ width: `${fixed.recovery_rate * 100}%` }}
            transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1], delay: 0.4 }}
          />
          <span className="val">{(eng.recovery_rate * 100).toFixed(1)}% recovered</span>
        </div>
      </div>
      <div className="row wrap" style={{ gap: 20, marginTop: 4, paddingLeft: 206 }}>
        <span className="small"><span className="dot-lg" style={{ background: "#2f7ad0", marginRight: 7 }} />Recovered by retries ({(fixed.recovery_rate * 100).toFixed(0)}%)</span>
        <span className="small"><span className="dot-lg" style={{ background: "var(--green)", marginRight: 7 }} />Added by the agent</span>
      </div>
    </div>
  );
}

export function Overview() {
  const { metrics } = useMetrics();
  if (!metrics) return <div className="soon">Loading…</div>;
  const p = metrics.holdout.policies;
  const eng = p.engine, fixed = p.fixed_retry;
  const rel = (metrics.holdout.uplift.vs_fixed_retry.recovery_rate_rel) * 100;

  const classes = Object.keys(eng.by_class_rate).sort(
    (a, b) => eng.by_class_rate[b] - eng.by_class_rate[a]
  );

  return (
    <div>
      <div className="page-h">
        <h1>Overview</h1>
        <p>Held-out performance across {(eng.total || 9000).toLocaleString("en-IN")} unseen failed charges.</p>
      </div>

      <div className="kpi-grid">
        <Card className="kpi-card">
          <div className="kpi-v green"><Counter value={eng.recovery_rate * 100} format={(n) => n.toFixed(1)} />%</div>
          <div className="kpi-l">Recovery rate</div>
        </Card>
        <Card className="kpi-card">
          <div className="kpi-v">{formatINR(eng.revenue_recovered_paise)}</div>
          <div className="kpi-l">Revenue recovered</div>
        </Card>
        <Card className="kpi-card">
          <div className="kpi-v">+<Counter value={rel} format={(n) => n.toFixed(0)} />%</div>
          <div className="kpi-l">Relative uplift</div>
        </Card>
        <Card className="kpi-card">
          <div className="kpi-v">{formatINR(eng.revenue_total_paise)}</div>
          <div className="kpi-l">At risk</div>
        </Card>
      </div>

      <div style={{ marginTop: 26 }}>
        <div className="section-title">Recovery funnel<span className="st-sub">from failure to reclaimed revenue</span></div>
        <Card><Funnel eng={eng} fixed={fixed} /></Card>
      </div>

      <div style={{ marginTop: 26 }}>
        <div className="section-title">Recovery by failure class<span className="st-sub">agent vs. fixed retry</span></div>
        <Card>
          <div className="bc-list">
            {classes.map((c) => (
              <div className="bc-row" key={c}>
                <span className="bcn">{classLabel(c)}</span>
                <div className="bct"><Bar value={eng.by_class_rate[c]} tone="green" /></div>
                <span className="bcv">
                  {((fixed.by_class_rate[c] || 0) * 100).toFixed(0)}% → <b>{(eng.by_class_rate[c] * 100).toFixed(0)}%</b>
                </span>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}
