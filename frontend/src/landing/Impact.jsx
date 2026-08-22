import React from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { Reveal, Counter, Button, Pill, Meter, Icon, fadeUp, stagger } from "../components/ui.jsx";
import { formatINR } from "../api.js";
import { POLICY_ORDER, POLICY_LABEL, classLabel } from "../lib/labels.js";

const CLASS_ORDER = [
  "needs_card_update",
  "needs_reauth",
  "insufficient_funds",
  "soft_decline",
  "transient",
  "hard_decline",
];

export function Impact({ metrics }) {
  const policies = metrics?.holdout?.policies || {};
  const engine = policies.engine;
  const fixed = policies.fixed_retry;
  const up = metrics?.holdout?.uplift?.vs_fixed_retry;
  const maxRate = Math.max(...POLICY_ORDER.map((p) => policies[p]?.recovery_rate || 0), 0.01);

  return (
    <section className="section impact" id="impact">
      <div className="container">
        <Reveal className="section__head">
          <span className="eyebrow pos">The proof</span>
          <h2 className="section__title">
            Measured on 9,000 unseen
            <br />
            failed charges.
          </h2>
          <p className="section__lede">
            A frozen holdout (seed 9999, never trained on). Every policy faces the{" "}
            <em>identical</em> hidden ground truth, so the gap is attributable skill — not
            luck.
          </p>
        </Reveal>

        {/* headline deltas */}
        <div className="impact__headline">
          <Reveal className="impact__hcard card card--glow" variants={fadeUp}>
            <div className="stat__label">Recovery rate</div>
            <div className="impact__hval tnum">
              <Counter to={(engine?.recovery_rate ?? 0.677) * 100} format={(v) => v.toFixed(1)} />%
            </div>
            <Pill tone="pos">
              +{((up?.recovery_rate_abs ?? 0.206) * 100).toFixed(1)} pts vs default
            </Pill>
          </Reveal>
          <Reveal className="impact__hcard card" variants={fadeUp}>
            <div className="stat__label">Revenue won back</div>
            <div className="impact__hval tnum">{formatINR(engine?.revenue_recovered_paise ?? 89944110000)}</div>
            <Pill tone="pos">+{formatINR(up?.revenue_recovered_delta_paise ?? 264419600)} recovered</Pill>
          </Reveal>
          <Reveal className="impact__hcard card" variants={fadeUp}>
            <div className="stat__label">Bank retries used</div>
            <div className="impact__hval tnum">{(engine?.retries ?? 13012).toLocaleString("en-IN")}</div>
            <Pill tone="cool">≈half of the {(fixed?.retries ?? 26361).toLocaleString("en-IN")} default</Pill>
          </Reveal>
        </div>

        {/* policy ladder */}
        <Reveal className="impact__ladder card" variants={fadeUp}>
          {POLICY_ORDER.map((p) => {
            const d = policies[p];
            if (!d) return null;
            const isEngine = p === "engine";
            return (
              <div key={p} className={`ladder__row ${isEngine ? "ladder__row--win" : ""}`}>
                <span className="ladder__name">
                  {POLICY_LABEL[p]}
                  {isEngine && <Icon name="bolt" size={13} />}
                </span>
                <span className="ladder__meter">
                  <Meter value={d.recovery_rate / maxRate} tone={isEngine ? "pos" : "neutral"} height={10} />
                </span>
                <span className="ladder__rate tnum">{(d.recovery_rate * 100).toFixed(1)}%</span>
                <span className="ladder__rev tnum">{formatINR(d.revenue_recovered_paise)}</span>
              </div>
            );
          })}
          <div className="ladder__foot mono">recovery rate · revenue recovered</div>
        </Reveal>

        {/* per-class wins */}
        <Reveal className="section__head section__head--sub">
          <h3 className="impact__subtitle">It wins biggest where a blind retry is useless.</h3>
        </Reveal>
        <motion.div
          className="impact__classes"
          variants={stagger(0.05)}
          initial="hidden"
          whileInView="show"
          viewport={{ once: true, margin: "-8% 0px" }}
        >
          {CLASS_ORDER.map((c) => {
            const f = fixed?.by_class_rate?.[c] ?? 0;
            const e = engine?.by_class_rate?.[c] ?? 0;
            return (
              <motion.div className="cwin card card--hover" key={c} variants={fadeUp}>
                <div className="cwin__name">{classLabel(c)}</div>
                <div className="cwin__bars">
                  <div className="cwin__bar">
                    <span className="cwin__tag mono">fixed</span>
                    <Meter value={f} tone="neutral" height={6} />
                    <span className="cwin__pct tnum">{(f * 100).toFixed(0)}%</span>
                  </div>
                  <div className="cwin__bar">
                    <span className="cwin__tag mono cwin__tag--pos">engine</span>
                    <Meter value={e} tone="pos" height={6} />
                    <span className="cwin__pct tnum cwin__pct--pos">{(e * 100).toFixed(0)}%</span>
                  </div>
                </div>
              </motion.div>
            );
          })}
        </motion.div>
      </div>
    </section>
  );
}

/* ---------------------------------------------------------------- CTA */

export function Gateway() {
  return (
    <section className="section cta">
      <div className="container">
        <Reveal className="cta__card card card--glow" variants={fadeUp}>
          <span className="eyebrow pos">Run it yourself</span>
          <h2 className="cta__title">
            The story ends where
            <br />
            the work begins.
          </h2>
          <p>
            Step into the operating console — hand the engine a live failed charge, watch it
            diagnose, decide, and author a recovery in real time.
          </p>
          <div className="cta__actions">
            <Button as={Link} to="/dashboard" variant="primary" size="lg">
              Enter the console <Icon name="arrow" size={17} />
            </Button>
          </div>
          <div className="cta__foot mono">
            Simulation-first · credential-optional · reproducible on seed 9999
          </div>
        </Reveal>
      </div>
      <footer className="lp__footer container">
        <span>AI Revenue Recovery</span>
        <span className="lp__footer-dim">Razorpay AI Buildathon 2026 · Track 3</span>
      </footer>
    </section>
  );
}
