import React, { useState } from "react";
import { motion } from "framer-motion";
import { Card } from "../components/primitives.jsx";
import { Bar } from "../components/Bar.jsx";
import { actionLabel, classLabel } from "../lib/labels.js";
import { useMetrics } from "../lib/useData.js";

export function LearningConsole() {
  const { metrics } = useMetrics();
  const [cls, setCls] = useState(null);
  if (!metrics) return <div className="soon">Loading…</div>;

  const bandit = metrics.holdout.bandit || {};
  const byClassEng = metrics.holdout.policies.engine.by_class_rate || {};
  const byClassFixed = metrics.holdout.policies.fixed_retry.by_class_rate || {};
  // Most-informative classes first (more arms tried = a richer comparison).
  const classes = Object.keys(bandit).sort(
    (a, b) => Object.keys(bandit[b]).length - Object.keys(bandit[a]).length
  );
  const active = cls && bandit[cls] ? cls : classes[0];
  const arms = bandit[active] || {};
  const ranked = Object.entries(arms).sort((a, b) => b[1] - a[1]);
  const max = Math.max(0.01, ...ranked.map(([, v]) => v));
  const [bestArm, bestRate] = ranked[0] || ["—", 0];

  return (
    <div>
      <div className="page-h">
        <h1>Learning</h1>
        <p>What the contextual bandit learned — the best intervention per failure class, from real outcomes.</p>
      </div>

      <div className="learn-tabs">
        {classes.map((c) => (
          <button key={c} className={`filter-chip ${c === active ? "active" : ""}`} onClick={() => setCls(c)}>
            {classLabel(c)}
          </button>
        ))}
      </div>

      <motion.div key={active} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
        <Card>
          <div className="learn-headline">
            <span className="lh-v">{(bestRate * 100).toFixed(0)}%</span>
            <div>
              <div className="lh-a">{actionLabel(bestArm)}</div>
              <div className="lh-l">learned best action for {classLabel(active)}</div>
            </div>
          </div>

          <div className="d-k" style={{ marginBottom: 12 }}>Success rate by action tried</div>
          <div className="alt-list">
            {ranked.map(([arm, rate], i) => (
              <div className="alt-row" key={arm}>
                <span className="aln" style={i === 0 ? { color: "var(--green-soft)", fontWeight: 550 } : null}>
                  {actionLabel(arm)}
                </span>
                <div className="alt"><Bar value={rate} max={max} tone={i === 0 ? "green" : "blue"} delay={i * 0.06} /></div>
                <span className="alv">{(rate * 100).toFixed(0)}%</span>
              </div>
            ))}
          </div>
        </Card>

        <Card style={{ marginTop: 16 }}>
          <div className="d-k" style={{ marginBottom: 12 }}>Why it matters</div>
          <p className="body" style={{ margin: 0, lineHeight: 1.6 }}>
            A blind retry recovers <b style={{ color: "var(--text)" }}>{((byClassFixed[active] || 0) * 100).toFixed(0)}%</b> of{" "}
            {classLabel(active).toLowerCase()} failures. By preferring{" "}
            <b style={{ color: "var(--green-soft)" }}>{actionLabel(bestArm).toLowerCase()}</b>, the agent recovers{" "}
            <b style={{ color: "var(--green-soft)" }}>{((byClassEng[active] || 0) * 100).toFixed(0)}%</b> — and it keeps
            adjusting as new outcomes arrive.
          </p>
        </Card>
      </motion.div>
    </div>
  );
}
