import React from "react";
import { Reveal, Counter, Pill, Meter, Icon, Card, fadeUp, stagger } from "../components/ui.jsx";
import { motion } from "framer-motion";
import { classLabel, actionLabel } from "../lib/labels.js";

/* --------------------------------------------------------- Predict / ML */

// Illustrative retry-success by day-relative-to-salary — the curve the timing
// model recovers from data (funds peak on payday, decay after).
const TIMING = [0.34, 0.3, 0.28, 0.31, 0.4, 0.62, 0.86, 0.78, 0.6, 0.48, 0.4, 0.36, 0.33, 0.31];
const PEAK = 6;

export function Intelligence({ metrics }) {
  const auc = metrics?.holdout?.engine_prediction_auc ?? 0.6644;
  const maxT = Math.max(...TIMING);
  return (
    <section className="section intel" id="engine">
      <div className="container intel__grid">
        <Reveal className="intel__copy">
          <span className="eyebrow" style={{ color: "var(--cool)" }}>
            Predict
          </span>
          <h2 className="section__title">
            It waits for payday
            <br />
            instead of hammering.
          </h2>
          <p className="section__lede">
            Two gradient-boosted models over the same feature vector: one scores{" "}
            <strong>P(recover)</strong> for triage, the other scans the next 14 days × hours
            to find the <strong>single best retry moment</strong> — salary-cycle aware, learned
            purely from observable signals.
          </p>
          <div className="intel__auc">
            <div className="stat">
              <div className="stat__label">Held-out triage AUC</div>
              <div className="stat__value tnum">
                <Counter to={auc} format={(v) => v.toFixed(3)} />
              </div>
            </div>
            <Pill tone="cool">no latents fed in — no leakage</Pill>
          </div>
        </Reveal>

        <Reveal className="intel__viz card" variants={fadeUp}>
          <div className="viz__head">
            <span className="mono">P(retry succeeds)</span>
            <span className="mono viz__head-dim">by day around salary credit</span>
          </div>
          <div className="timing">
            {TIMING.map((v, i) => (
              <div className="timing__col" key={i}>
                <motion.div
                  className={`timing__bar ${i === PEAK ? "timing__bar--peak" : ""}`}
                  initial={{ height: 0 }}
                  whileInView={{ height: `${(v / maxT) * 100}%` }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.6, delay: i * 0.03, ease: [0.22, 1, 0.36, 1] }}
                />
              </div>
            ))}
          </div>
          <div className="timing__axis mono">
            <span>−6d</span>
            <span className="timing__axis-peak">payday</span>
            <span>+7d</span>
          </div>
        </Reveal>
      </div>
    </section>
  );
}

/* ---------------------------------------------------------------- Act */

export function Act() {
  return (
    <section className="section act">
      <div className="container act__grid">
        <Reveal className="act__phone card" variants={fadeUp}>
          <div className="msg__top">
            <span className="msg__brand">
              <Icon name="message" size={15} /> WhatsApp · to Priya
            </span>
            <Pill tone="pos" soft>
              matched · hi
            </Pill>
          </div>
          <div className="msg__bubble">
            <p>
              Priya, aapka <strong>₹499</strong> ka UPI autopay fail ho gaya hai — jaldi se
              fund add kijiye aur plan ko active rakhiye 👇
            </p>
            <a className="msg__link" href="#act" onClick={(e) => e.preventDefault()}>
              <Icon name="link" size={15} /> rzp.io/i/pay-499 <Icon name="arrow-up-right" size={14} />
            </a>
            <span className="msg__time mono">now · authored by Groq</span>
          </div>
          <div className="msg__langs">
            {["हिन्दी", "Hinglish", "English"].map((l) => (
              <span key={l} className="msg__lang">
                {l}
              </span>
            ))}
          </div>
        </Reveal>

        <Reveal className="act__copy">
          <span className="eyebrow">Act</span>
          <h2 className="section__title">
            A message a human
            <br />
            would actually answer.
          </h2>
          <p className="section__lede">
            The engine writes a personalised, multilingual dunning message — in the
            customer&rsquo;s language, on their preferred channel — and attaches a{" "}
            <strong>real Razorpay payment link</strong> for one-tap recovery. An LLM authors
            the copy; a deterministic template is the always-ready fallback.
          </p>
          <ul className="act__points">
            <li>
              <Icon name="check" size={16} /> Channel &amp; language matched to the customer
            </li>
            <li>
              <Icon name="check" size={16} /> One-tap Razorpay test-mode payment link
            </li>
            <li>
              <Icon name="check" size={16} /> Never blocks on the model — templates always ready
            </li>
          </ul>
        </Reveal>
      </div>
    </section>
  );
}

/* ---------------------------------------------------------------- Learning */

export function Learning({ bandit }) {
  const data = bandit || {};
  const rows = Object.entries(data)
    .map(([cls, actions]) => {
      const best = Object.entries(actions).sort((a, b) => b[1] - a[1])[0];
      return best ? { cls, action: best[0], rate: best[1] } : null;
    })
    .filter(Boolean)
    .sort((a, b) => b.rate - a.rate);

  if (!rows.length) return null;
  const max = Math.max(...rows.map((r) => r.rate));

  return (
    <section className="section learn">
      <div className="container">
        <Reveal className="section__head">
          <span className="eyebrow">Decide · learn</span>
          <h2 className="section__title">What the bandit converged to.</h2>
          <p className="section__lede">
            A contextual bandit corrects the model&rsquo;s expected-value estimates from live
            outcomes — so the best action per failure class is <em>learned</em>, not
            hard-coded.
          </p>
        </Reveal>

        <motion.div
          className="learn__grid card"
          variants={stagger(0.05)}
          initial="hidden"
          whileInView="show"
          viewport={{ once: true, margin: "-8% 0px" }}
        >
          {rows.map((r) => (
            <motion.div className="learn__row" key={r.cls} variants={fadeUp}>
              <span className="learn__cls">{classLabel(r.cls)}</span>
              <span className="learn__act">
                <Icon name="arrow" size={13} /> {actionLabel(r.action)}
              </span>
              <span className="learn__meter">
                <Meter value={r.rate / max} tone="pos" height={6} />
              </span>
              <span className="learn__rate tnum">{(r.rate * 100).toFixed(1)}%</span>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
