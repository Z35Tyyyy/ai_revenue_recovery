import React, { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Button, Pill, Icon, Card } from "../components/ui.jsx";
import { api } from "../api.js";

// Interactive proof that the SAME agent handles the other revenue-at-risk sources:
// hand it a checkout or an invoice, it diagnoses the root cause, picks the right
// intervention, and lays out the bounded (compliant, stopping-ruled) workflow.
const SOURCES = {
  checkout_abandonment: {
    label: "Abandoned checkout",
    unit: "cart",
    classes: [
      { key: "payment_friction", label: "Payment friction" },
      { key: "distraction", label: "Distraction" },
      { key: "account_friction", label: "Sign-up wall" },
      { key: "price_shock", label: "Price / shipping shock" },
      { key: "comparison", label: "Just comparing" },
    ],
  },
  overdue_receivable: {
    label: "Overdue invoice",
    unit: "invoice",
    classes: [
      { key: "oversight", label: "Oversight (<30d)" },
      { key: "cashflow", label: "Cash-flow tight (30–60d)" },
      { key: "chronic_late", label: "Chronically late" },
      { key: "dispute", label: "Disputed invoice" },
      { key: "distressed", label: "Distressed (90d+)" },
    ],
  },
};

export function RiskAgent({ source }) {
  const spec = SOURCES[source];
  const [cls, setCls] = useState(spec.classes[0].key);
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);

  const run = async () => {
    setBusy(true);
    try {
      setResult(await api.riskPlan(source, cls));
    } catch {
      /* offline */
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="agent__grid">
      <Card className="agent__form">
        <div className="agent__form-head">
          <h2>{spec.label}</h2>
          <Pill tone="cool">{spec.unit}</Pill>
        </div>
        <label className="field">
          <span className="field__label">Root cause — what the detector flags</span>
          <select className="input" value={cls} onChange={(e) => setCls(e.target.value)}>
            {spec.classes.map((c) => (
              <option key={c.key} value={c.key}>{c.label}</option>
            ))}
          </select>
        </label>
        <Button variant="primary" size="lg" onClick={run} disabled={busy} className="agent__go">
          {busy ? "Diagnosing…" : "Diagnose & plan"} <Icon name="bolt" size={16} />
        </Button>
        <p className="agent__reasoning-foot mono">
          Same detect → decide → bounded-execute agent as failed payments — a different trigger and
          intervention menu, one loop.
        </p>
      </Card>

      <div className="agent__result">
        <AnimatePresence mode="wait">
          {!result ? (
            <motion.div
              key="empty"
              className="agent__empty card"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <Icon name="spark" size={26} />
              <p>The diagnosis, the chosen intervention, and the bounded recovery workflow appear here.</p>
            </motion.div>
          ) : (
            <motion.div
              key="res"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
              className="agent__res-inner"
            >
              <Card className="agent__verdict" glow>
                <div className="verdict__top">
                  <span className="verdict__lab">Recommended intervention</span>
                  <Pill tone={result.stopped ? "warn" : "pos"}>{result.class_label}</Pill>
                </div>
                <div className={`verdict__action verdict__action--${result.stopped ? "neg" : "pos"}`}>
                  {result.action_label}
                </div>
                <div className="verdict__meta">
                  <span>
                    Recoverability{" "}
                    <strong className="tnum">{Math.round((result.recoverability || 0) * 100)}%</strong>
                  </span>
                </div>
                <p className="verdict__note">{result.why}</p>
              </Card>

              <Card className="agent__sched">
                <div className="agent__msg-head">
                  <h3><Icon name="bolt" size={15} /> Bounded recovery workflow</h3>
                  <Pill tone="neutral">stop after {result.stop_at}</Pill>
                </div>
                <ol className="riskladder">
                  {(result.ladder || []).map((step, i) => (
                    <li key={i} className="riskladder__step">
                      <span className="riskladder__n mono">{i + 1}</span>
                      <span>{step}</span>
                    </li>
                  ))}
                  <li className="riskladder__step riskladder__step--stop">
                    <span className="riskladder__n mono">
                      <Icon name="close" size={11} />
                    </span>
                    <span>
                      Stopping rule —{" "}
                      {result.stopped
                        ? "already below the recoverability floor: don't spend, let it go"
                        : `after ${result.stop_at} compliant touches, stop`}
                    </span>
                  </li>
                </ol>
              </Card>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
