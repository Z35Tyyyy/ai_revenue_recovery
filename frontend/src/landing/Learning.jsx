import React from "react";
import { Reveal } from "../components/Reveal.jsx";
import { Bar } from "../components/Bar.jsx";
import { Eyebrow } from "../components/primitives.jsx";
import { actionLabel, classLabel } from "../lib/labels.js";

const LOOP = ["Decision", "Action", "Outcome", "Reward", "Learning", "Better decision"];
const FOCUS = "insufficient_funds";

export function Learning({ bandit }) {
  const arms = (bandit && bandit[FOCUS]) || {
    retry_optimal: 0.326, retry_now: 0.289, dunning_nudge: 0.251,
  };
  const ranked = Object.entries(arms).sort((a, b) => b[1] - a[1]);
  const max = Math.max(...ranked.map(([, v]) => v), 0.01);

  return (
    <section>
      <div className="container">
        <div className="section-head">
          <Reveal><Eyebrow>The learning loop</Eyebrow></Reveal>
          <Reveal delay={0.06}>
            <h2 className="h2" style={{ marginTop: 16 }}>It gets smarter after every outcome.</h2>
          </Reveal>
          <Reveal delay={0.12}>
            <p className="lead">
              Every recovery is a lesson. A contextual bandit tracks which intervention actually
              works for each failure class, and shifts the agent toward it — no retraining required.
            </p>
          </Reveal>
        </div>

        <div className="learn-grid">
          <Reveal delay={0.1}>
            <div className="loop">
              {LOOP.map((n, i) => (
                <React.Fragment key={n}>
                  <span className="lnode">{n}</span>
                  {i < LOOP.length - 1 && <span className="larrow">→</span>}
                </React.Fragment>
              ))}
            </div>
          </Reveal>

          <Reveal delay={0.16}>
            <div className="bandit-panel">
              <div className="bp-head">
                <span className="small">Learned success rate · {classLabel(FOCUS)}</span>
                <span className="chip good">converged</span>
              </div>
              {ranked.map(([arm, rate], i) => (
                <div className={`bandit-row ${i === 0 ? "best" : ""}`} key={arm}>
                  <span className="bn">{actionLabel(arm)}</span>
                  <div className="bt"><Bar value={rate} max={max} tone={i === 0 ? "green" : "blue"} delay={i * 0.08} /></div>
                  <span className="bv">{(rate * 100).toFixed(0)}%</span>
                </div>
              ))}
            </div>
          </Reveal>
        </div>
      </div>
    </section>
  );
}
