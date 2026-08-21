import React from "react";
import { Reveal, Stagger } from "../components/Reveal.jsx";
import { Eyebrow, Chip } from "../components/primitives.jsx";
import { FailCard, SCENARIOS } from "./FailCard.jsx";

export function Problem() {
  return (
    <section id="problem">
      <div className="container">
        <div className="section-head">
          <Reveal><Eyebrow>The problem</Eyebrow></Reveal>
          <Reveal delay={0.06}><h2 className="h2" style={{ marginTop: 16 }}>Every failed payment is a decision.</h2></Reveal>
          <Reveal delay={0.12}>
            <p className="lead">
              Subscription businesses lose 20–40% of recurring revenue to payments that fail for
              recoverable reasons. The customer never chose to leave — the charge just bounced.
            </p>
          </Reveal>
        </div>

        <div className="agent-stage">
          <Reveal delay={0.1}><FailCard /></Reveal>
          <Stagger gap={0.08} className="action-list">
            {SCENARIOS.map((s) => (
              <Stagger.Item key={s.reason} className="action-row">
                <span className="an">{s.label}</span>
                <div style={{ justifySelf: "end" }}><Chip mono>{s.reason}</Chip></div>
              </Stagger.Item>
            ))}
          </Stagger>
        </div>

        <Reveal>
          <div className="beat">
            <span className="b1">Most systems retry.</span>
            <span className="b2">But retrying isn't <em>reasoning</em>.</span>
          </div>
        </Reveal>
      </div>
    </section>
  );
}
