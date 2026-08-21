import React from "react";
import { Reveal } from "../components/Reveal.jsx";
import { Counter } from "../components/Counter.jsx";
import { Bar } from "../components/Bar.jsx";
import { Eyebrow } from "../components/primitives.jsx";

export function Impact({ metrics }) {
  const p = metrics?.holdout?.policies;
  const up = metrics?.holdout?.uplift?.vs_fixed_retry;
  const eng = p?.engine?.recovery_rate ?? 0.6766;
  const fixed = p?.fixed_retry?.recovery_rate ?? 0.4706;
  const generic = p?.generic_dunning?.recovery_rate ?? 0.5317;
  const rel = (up?.recovery_rate_rel ?? 0.4378) * 100;
  const revLakh = (p?.engine?.revenue_recovered_paise ?? 899441100) / 100 / 1e5;

  const rows = [
    { label: "Fixed retries", rate: fixed, tone: "muted" },
    { label: "Retries + generic email", rate: generic, tone: "blue" },
    { label: "AI Revenue Recovery", rate: eng, tone: "green", eng: true },
  ];
  const max = eng;

  return (
    <section className="impact">
      <div className="impact-atmos" />
      <div className="container" style={{ position: "relative" }}>
        <Reveal><Eyebrow>The impact</Eyebrow></Reveal>
        <Reveal delay={0.06}>
          <div className="impact-num" style={{ marginTop: 24 }}>
            <Counter value={eng * 100} format={(n) => n.toFixed(1)} />%
          </div>
        </Reveal>
        <Reveal delay={0.12}><div className="cap">Recovery rate on unseen failures</div></Reveal>

        <div className="compare">
          {rows.map((r) => (
            <div className={`crow ${r.eng ? "eng" : ""}`} key={r.label}>
              <span className="cl">{r.label}</span>
              <div className="ct"><Bar value={r.rate} max={max} tone={r.tone} /></div>
              <span className="cv">{(r.rate * 100).toFixed(1)}%</span>
            </div>
          ))}
        </div>

        <div className="impact-foot">
          <div>
            <div className="k green">+<Counter value={rel} format={(n) => n.toFixed(0)} />%</div>
            <div className="l">relative uplift vs default</div>
          </div>
          <div>
            <div className="k">₹<Counter value={revLakh} duration={1.6} format={(n) => n.toFixed(2)} />L</div>
            <div className="l">recovered on the holdout</div>
          </div>
        </div>
      </div>
    </section>
  );
}
