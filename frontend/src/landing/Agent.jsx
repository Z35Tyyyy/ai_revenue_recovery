import React from "react";
import { motion } from "framer-motion";
import { Reveal } from "../components/Reveal.jsx";
import { Bar } from "../components/Bar.jsx";
import { Eyebrow, Chip, Dot } from "../components/primitives.jsx";
import { viewport } from "../lib/motion.js";

// A representative decision for an expired-card failure — codes are the real engine
// actions; probabilities illustrate how the agent ranks them.
const ACTIONS = [
  { label: "Request card update", code: "request_card_update", p: 0.72, chosen: true },
  { label: "Send a reminder", code: "dunning_nudge", p: 0.31 },
  { label: "Switch payment method", code: "switch_method", p: 0.22 },
  { label: "Wait for the right moment", code: "retry_optimal", p: 0.14 },
  { label: "Retry now", code: "retry_now", p: 0.08 },
  { label: "Stop — unrecoverable", code: "give_up", p: 0.02 },
];

export function Agent() {
  return (
    <section>
      <div className="container">
        <div className="section-head">
          <Reveal><Eyebrow>The agent</Eyebrow></Reveal>
          <Reveal delay={0.06}>
            <h2 className="h2" style={{ marginTop: 16 }}>One payment. Multiple possible actions.</h2>
          </Reveal>
          <Reveal delay={0.12}>
            <p className="lead">
              The agent weighs every intervention by its expected recovered revenue, then commits
              to the one most likely to work — and skips the ones that can't.
            </p>
          </Reveal>
        </div>

        <div className="agent-stage">
          <motion.div
            className="action-list"
            initial="hidden"
            whileInView="show"
            viewport={viewport}
            variants={{ hidden: {}, show: { transition: { staggerChildren: 0.07 } } }}
          >
            {ACTIONS.map((a) => (
              <motion.div
                key={a.code}
                className={`action-row ${a.chosen ? "chosen" : ""}`}
                variants={{ hidden: { opacity: 0, y: 10 }, show: { opacity: 1, y: 0 } }}
              >
                <div>
                  <span className="an">
                    <Dot color={a.chosen ? "var(--green)" : "var(--text-faint)"} /> {a.label}
                  </span>
                  <div className="ac">{a.code}</div>
                </div>
                <div className="prob"><Bar value={a.p} tone={a.chosen ? "green" : "blue"} /></div>
              </motion.div>
            ))}
          </motion.div>

          <Reveal delay={0.15}>
            <div className="decision-card">
              <div className="dk">Selected action</div>
              <div className="dv">Request card update</div>
              <div className="dconf">
                <Chip variant="good">72% confidence</Chip>
              </div>
              <div className="dreason">
                Card update is the highest-performing intervention for this failure class.
                Retrying an expired card recovers only ~9% — so the agent asks the customer to
                update it instead, on their preferred channel.
              </div>
            </div>
          </Reveal>
        </div>
      </div>
    </section>
  );
}
