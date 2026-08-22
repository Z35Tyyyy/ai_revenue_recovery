import React from "react";
import { Reveal, Counter, Pill, Icon, stagger, fadeUp } from "../components/ui.jsx";
import { motion } from "framer-motion";

/* ------------------------------------------------------------- The leak */

export function Problem() {
  return (
    <section className="section problem" id="problem">
      <div className="container">
        <Reveal className="section__head">
          <span className="eyebrow neg">The leak</span>
          <h2 className="section__title">
            A fifth of your revenue quietly
            <br />
            drains out the back.
          </h2>
        </Reveal>

        <div className="problem__grid">
          <Reveal className="problem__stat card" variants={fadeUp}>
            <div className="problem__big tnum">
              <Counter to={40} />%
            </div>
            <p>
              of recurring revenue lost to <strong>involuntary</strong> churn — payments
              that failed for <em>recoverable</em> reasons. The customer never chose to
              leave.
            </p>
          </Reveal>

          <div className="problem__blunt">
            <Reveal className="blunt card" variants={fadeUp}>
              <span className="blunt__no mono">01</span>
              <h3>Fixed-schedule retries</h3>
              <p>
                One dumb retry, next day, same hour — for every failure. Whether the card
                is expired (pointless) or the customer is just mid-month broke (retry on
                salary day and it sails through).
              </p>
              <Pill tone="neg">blind</Pill>
            </Reveal>
            <Reveal className="blunt card" variants={fadeUp}>
              <span className="blunt__no mono">02</span>
              <h3>Generic dunning</h3>
              <p>
                A single templated &ldquo;your payment failed&rdquo; email, in English, to
                everyone — regardless of <em>why</em> it failed or <em>who</em> the
                customer is.
              </p>
              <Pill tone="neg">one-size</Pill>
            </Reveal>
          </div>
        </div>
      </div>
    </section>
  );
}

/* --------------------------------------------------------- Failure taxonomy */

const CLASSES = [
  { k: "transient", name: "Transient", ex: "Bank downtime, gateway blip", helps: true, fix: "Just retry — it clears", tone: "cool" },
  { k: "insufficient_funds", name: "Insufficient funds", ex: "No balance on debit day", helps: true, fix: "Wait for the salary window", tone: "warn" },
  { k: "soft_decline", name: "Soft decline", ex: "Do-not-honour, freq. exceeded", helps: true, fix: "Back off, retry smart", tone: "warn" },
  { k: "needs_card_update", name: "Card needs updating", ex: "Expired / disabled card", helps: false, fix: "Ask for a fresh card", tone: "neutral" },
  { k: "needs_reauth", name: "Needs re-auth", ex: "Mandate paused / revoked", helps: false, fix: "Re-authorise the mandate", tone: "neutral" },
  { k: "hard_decline", name: "Unrecoverable", ex: "Stolen, invalid, frozen", helps: false, fix: "Stop — don't waste spend", tone: "neg" },
];

export function Taxonomy() {
  return (
    <section className="section taxonomy">
      <div className="container">
        <Reveal className="section__head">
          <span className="eyebrow">Diagnose</span>
          <h2 className="section__title">Not all failures are equal.</h2>
          <p className="section__lede">
            Every raw Razorpay reason code maps to one of six recoverability classes. The
            class decides which actions even make sense — you can&rsquo;t retry an expired
            card into success.
          </p>
        </Reveal>

        <motion.div
          className="taxonomy__grid"
          variants={stagger(0.06)}
          initial="hidden"
          whileInView="show"
          viewport={{ once: true, margin: "-10% 0px" }}
        >
          {CLASSES.map((c) => (
            <motion.article key={c.k} className="tax card card--hover" variants={fadeUp}>
              <header className="tax__head">
                <h3>{c.name}</h3>
                <Pill tone={c.helps ? "pos" : c.tone === "neg" ? "neg" : "neutral"}>
                  {c.helps ? "retry helps" : "retry futile"}
                </Pill>
              </header>
              <p className="tax__ex mono">{c.ex}</p>
              <div className="tax__fix">
                <Icon name="arrow" size={14} />
                <span>{c.fix}</span>
              </div>
            </motion.article>
          ))}
        </motion.div>
      </div>
    </section>
  );
}

/* ---------------------------------------------------------------- The loop */

const STAGES = [
  { n: "01", icon: "spark", title: "Diagnose", body: "Map the raw bank code to a recoverability class." },
  { n: "02", icon: "clock", title: "Predict", body: "ML scores P(recover) and the optimal retry slot." },
  { n: "03", icon: "bolt", title: "Decide", body: "A bandit picks the action worth the most rupees." },
  { n: "04", icon: "message", title: "Act", body: "Personalised message + a real payment link." },
  { n: "05", icon: "check", title: "Measure", body: "Every outcome feeds back. The policy learns." },
];

export function Loop() {
  return (
    <section className="section loop">
      <div className="container">
        <Reveal className="section__head section__head--center">
          <span className="eyebrow">The closed loop</span>
          <h2 className="section__title">
            One decision loop, run for <em>every</em> failed charge.
          </h2>
        </Reveal>

        <motion.ol
          className="loop__track"
          variants={stagger(0.08)}
          initial="hidden"
          whileInView="show"
          viewport={{ once: true, margin: "-10% 0px" }}
        >
          {STAGES.map((s, i) => (
            <motion.li key={s.n} className="loop__stage" variants={fadeUp}>
              <div className="loop__node">
                <Icon name={s.icon} size={18} />
              </div>
              <span className="loop__n mono">{s.n}</span>
              <h3>{s.title}</h3>
              <p>{s.body}</p>
              {i < STAGES.length - 1 && <span className="loop__link" aria-hidden="true" />}
            </motion.li>
          ))}
        </motion.ol>
      </div>
    </section>
  );
}
