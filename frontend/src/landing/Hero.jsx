import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { motion, useReducedMotion } from "framer-motion";
import { Button, Counter, Icon } from "../components/ui.jsx";
import { formatINR } from "../api.js";

const ROWS = [
  { reason: "Card expired", amount: 49900, where: "Mumbai · hi", action: "Card update sent" },
  { reason: "Insufficient funds", amount: 129900, where: "Pune · en", action: "Retried on payday" },
  { reason: "Mandate paused", amount: 29900, where: "Chennai · ta", action: "Re-auth nudge" },
  { reason: "Bank downtime", amount: 89900, where: "Delhi · hi", action: "Retried in 20m" },
  { reason: "Do-not-honour", amount: 19900, where: "Jaipur · hi", action: "Retried optimally" },
];

function TickerRow({ row, recovered, i }) {
  return (
    <motion.div
      className={`tick ${recovered ? "tick--won" : "tick--fail"}`}
      layout
      initial={false}
    >
      <span className="tick__status">
        <span className="tick__dot" />
        {recovered ? (
          <motion.span
            key="won"
            initial={{ scale: 0.4, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
            className="tick__check"
          >
            <Icon name="check" size={13} />
          </motion.span>
        ) : null}
      </span>
      <span className="tick__reason">{row.reason}</span>
      <span className="tick__meta">{row.where}</span>
      <span className="tick__amount tnum">{formatINR(row.amount)}</span>
      <span className="tick__tag">{recovered ? row.action : "failed"}</span>
    </motion.div>
  );
}

function RecoveryTicker() {
  const reduce = useReducedMotion();
  const [n, setN] = useState(reduce ? ROWS.length : 0);

  useEffect(() => {
    if (reduce) return;
    const id = setInterval(() => {
      setN((prev) => (prev >= ROWS.length ? 0 : prev + 1));
    }, 1500);
    return () => clearInterval(id);
  }, [reduce]);

  const recoveredValue = ROWS.slice(0, n).reduce((s, r) => s + r.amount, 0);

  return (
    <div className="ticker card">
      <div className="ticker__head">
        <span className="eyebrow">Live recovery</span>
        <span className="ticker__won tnum">
          {formatINR(recoveredValue)} <span>won back</span>
        </span>
      </div>
      <div className="ticker__rows">
        {ROWS.map((row, i) => (
          <TickerRow key={i} row={row} i={i} recovered={i < n} />
        ))}
      </div>
      <div className="ticker__foot">
        <span className="mono">payment.failed</span>
        <Icon name="arrow" size={14} />
        <span className="mono ticker__foot-pos">recovered</span>
      </div>
    </div>
  );
}

export function Hero({ metrics }) {
  const eng = metrics?.holdout?.policies?.engine;
  const up = metrics?.holdout?.uplift?.vs_fixed_retry;
  const rate = eng ? eng.recovery_rate * 100 : 67.8;
  const absPts = up ? up.recovery_rate_abs * 100 : 20.7;
  const revenue = eng ? eng.revenue_recovered_paise : 910519800;

  return (
    <section className="hero" id="top">
      <div className="container hero__grid">
        <div className="hero__copy">
          <span className="eyebrow">Razorpay AI Buildathon · Track&nbsp;3</span>
          <h1 className="hero__title">
            Your customers
            <br />
            didn&rsquo;t leave.
            <br />
            <span className="hero__title-accent">The payment did.</span>
          </h1>
          <p className="hero__lede">
            20–40% of recurring revenue is lost to <em>involuntary</em> churn — cards
            that expired, funds that weren&rsquo;t there on debit day, mandates that
            lapsed. An agentic engine that diagnoses every failure, predicts the right
            moment, and wins the money back.
          </p>

          <div className="hero__cta">
            <Button as={Link} to="/dashboard" variant="primary" size="lg">
              Enter the console <Icon name="arrow" size={17} />
            </Button>
            <Button as="a" href="#problem" variant="quiet" size="lg">
              See how it works
            </Button>
          </div>

          <div className="hero__stats">
            <div className="hero__stat">
              <div className="hero__stat-val tnum">
                <Counter to={rate} format={(v) => v.toFixed(1)} />%
              </div>
              <div className="hero__stat-lab">recovery rate</div>
            </div>
            <div className="hero__stat">
              <div className="hero__stat-val tnum hero__stat-val--pos">
                +<Counter to={absPts} format={(v) => v.toFixed(1)} /> pts
              </div>
              <div className="hero__stat-lab">vs the default retry</div>
            </div>
            <div className="hero__stat">
              <div className="hero__stat-val tnum">{formatINR(revenue)}</div>
              <div className="hero__stat-lab">won back on holdout</div>
            </div>
          </div>
        </div>

        <div className="hero__visual">
          <RecoveryTicker />
        </div>
      </div>
      <div className="hero__scrollcue" aria-hidden="true">
        <span className="mono">scroll</span>
        <span className="hero__scrollcue-line" />
      </div>
    </section>
  );
}
