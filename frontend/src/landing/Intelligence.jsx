import React from "react";
import { Reveal, Stagger } from "../components/Reveal.jsx";
import { Pipeline } from "../components/Pipeline.jsx";
import { Eyebrow } from "../components/primitives.jsx";

const STAGES = [
  { label: "Classify" },
  { label: "Context" },
  { label: "Choose action" },
  { label: "Intervene" },
  { label: "Recover" },
];

const SIGNALS = [
  { t: "Failure class", d: "why the charge bounced" },
  { t: "Amount", d: "what's at stake" },
  { t: "Payment method", d: "card, UPI, mandate" },
  { t: "Salary day", d: "when money arrives" },
  { t: "Channel", d: "WhatsApp, email, SMS" },
  { t: "Language", d: "Hindi, Hinglish, English" },
  { t: "Customer context", d: "tenure & history" },
  { t: "Action performance", d: "what worked before" },
];

export function Intelligence() {
  return (
    <section>
      <div className="container">
        <div className="section-head">
          <Reveal><Eyebrow>The intelligence</Eyebrow></Reveal>
          <Reveal delay={0.06}>
            <h2 className="h2" style={{ marginTop: 16 }}>It doesn't retry everything. It reasons.</h2>
          </Reveal>
          <Reveal delay={0.12}>
            <p className="lead">
              Each failure enters a pipeline that understands the situation before it acts —
              then picks the intervention most likely to recover the payment.
            </p>
          </Reveal>
        </div>

        <Reveal delay={0.1}>
          <div style={{ marginTop: 40 }}>
            <Pipeline stages={STAGES} orientation="horizontal" accentIndex={4} />
          </div>
        </Reveal>

        <Stagger gap={0.06} className="signals">
          {SIGNALS.map((s) => (
            <Stagger.Item key={s.t} className="signal">
              <div className="st">{s.t}</div>
              <div className="sd">{s.d}</div>
            </Stagger.Item>
          ))}
        </Stagger>
      </div>
    </section>
  );
}
