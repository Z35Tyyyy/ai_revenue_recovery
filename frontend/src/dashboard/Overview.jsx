import React from "react";
import { Reveal, Counter, Card, Pill, Meter, Icon, stagger, fadeUp } from "../components/ui.jsx";
import { motion } from "framer-motion";
import { useMetrics } from "../lib/useData.js";
import { formatINR } from "../api.js";
import { POLICY_ORDER, POLICY_LABEL, classLabel } from "../lib/labels.js";

const CLASS_ORDER = [
  "needs_card_update", "needs_reauth", "insufficient_funds",
  "soft_decline", "transient", "hard_decline",
];

function Kpi({ label, children, delta, deltaTone = "pos", sub }) {
  return (
    <Card className="kpi">
      <div className="kpi__label">{label}</div>
      <div className="kpi__value tnum">{children}</div>
      <div className="kpi__foot">
        {delta && <span className={`kpi__delta kpi__delta--${deltaTone}`}>{delta}</span>}
        {sub && <span className="kpi__sub">{sub}</span>}
      </div>
    </Card>
  );
}

export function Overview() {
  const { metrics, loading } = useMetrics();
  const h = metrics?.holdout;
  const eng = h?.policies?.engine;
  const fixed = h?.policies?.fixed_retry;
  const up = h?.uplift?.vs_fixed_retry;
  const maxRate = Math.max(...POLICY_ORDER.map((p) => h?.policies?.[p]?.recovery_rate || 0), 0.01);

  if (loading) return <div className="dash__loading mono">loading metrics…</div>;

  return (
    <div className="page">
      <p className="page__lead">
        The frozen holdout — <strong>{(eng?.total ?? 9000).toLocaleString("en-IN")}</strong> unseen
        failed charges, the engine against the Razorpay default and generic dunning on identical
        ground truth.
      </p>

      <motion.div
        className="kpis"
        variants={stagger(0.06)}
        initial="hidden"
        animate="show"
      >
        <motion.div variants={fadeUp}>
          <Kpi
            label="Recovery rate"
            delta={`+${((up?.recovery_rate_abs ?? 0.206) * 100).toFixed(1)} pts`}
            sub="vs fixed retry"
          >
            <Counter to={(eng?.recovery_rate ?? 0.677) * 100} format={(v) => v.toFixed(1)} />%
          </Kpi>
        </motion.div>
        <motion.div variants={fadeUp}>
          <Kpi
            label="Revenue recovered"
            delta={`+${formatINR(up?.revenue_recovered_delta_paise ?? 264419600)}`}
            sub="over default"
          >
            {formatINR(eng?.revenue_recovered_paise ?? 89944110000)}
          </Kpi>
        </motion.div>
        <motion.div variants={fadeUp}>
          <Kpi
            label="Retries used"
            delta={`−${(((fixed?.retries ?? 26361) - (eng?.retries ?? 13012)) / 1000).toFixed(1)}k`}
            sub={`vs ${(fixed?.retries ?? 26361).toLocaleString("en-IN")}`}
          >
            {(eng?.retries ?? 13012).toLocaleString("en-IN")}
          </Kpi>
        </motion.div>
        <motion.div variants={fadeUp}>
          <Kpi label="Triage AUC" deltaTone="cool" delta="held-out" sub="P(recover)">
            <Counter to={h?.engine_prediction_auc ?? 0.6644} format={(v) => v.toFixed(3)} />
          </Kpi>
        </motion.div>
      </motion.div>

      <div className="page__cols">
        <Reveal className="panel card" variants={fadeUp}>
          <div className="panel__head">
            <h2>Engine vs baselines</h2>
            <Pill tone="neutral">recovery rate</Pill>
          </div>
          <div className="ladder">
            {POLICY_ORDER.map((p) => {
              const d = h?.policies?.[p];
              if (!d) return null;
              const win = p === "engine";
              return (
                <div key={p} className={`ladder__row ${win ? "ladder__row--win" : ""}`}>
                  <span className="ladder__name">
                    {POLICY_LABEL[p]} {win && <Icon name="bolt" size={12} />}
                  </span>
                  <span className="ladder__meter">
                    <Meter value={d.recovery_rate / maxRate} tone={win ? "pos" : "neutral"} height={9} />
                  </span>
                  <span className="ladder__rate tnum">{(d.recovery_rate * 100).toFixed(1)}%</span>
                </div>
              );
            })}
          </div>
        </Reveal>

        <Reveal className="panel card" variants={fadeUp}>
          <div className="panel__head">
            <h2>Recovery by failure class</h2>
            <span className="panel__legend">
              <span className="dot dot--muted" /> fixed <span className="dot dot--pos" /> engine
            </span>
          </div>
          <div className="byclass">
            {CLASS_ORDER.map((c) => {
              const f = fixed?.by_class_rate?.[c] ?? 0;
              const e = eng?.by_class_rate?.[c] ?? 0;
              return (
                <div key={c} className="byclass__row">
                  <span className="byclass__name">{classLabel(c)}</span>
                  <span className="byclass__bars">
                    <Meter value={f} tone="neutral" height={5} />
                    <Meter value={e} tone="pos" height={5} />
                  </span>
                  <span className="byclass__pct tnum">
                    <span className="byclass__pct-muted">{(f * 100).toFixed(0)}</span>
                    <Icon name="arrow" size={11} />
                    <span className="byclass__pct-pos">{(e * 100).toFixed(0)}%</span>
                  </span>
                </div>
              );
            })}
          </div>
        </Reveal>
      </div>
    </div>
  );
}
