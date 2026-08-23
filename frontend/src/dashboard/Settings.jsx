import React from "react";
import { Card, Pill, Icon } from "../components/ui.jsx";
import { useHealth, useMetrics } from "../lib/useData.js";

function Cap({ label, on, value, tone, note }) {
  return (
    <Card className="cap">
      <div className="cap__top">
        <span className="cap__label">{label}</span>
        <span className={`cap__dot cap__dot--${on ? tone || "pos" : "off"}`} />
      </div>
      <div className="cap__value">{value}</div>
      {note && <div className="cap__note">{note}</div>}
    </Card>
  );
}

export function Settings() {
  const { health } = useHealth();
  const { metrics } = useMetrics();
  const hd = metrics?.holdout?.holdout || {};
  const episodes = health?.sample_cases ?? metrics?.holdout?.sample_cases;

  return (
    <div className="page">
      <p className="page__lead">
        Runtime capabilities and the reproducibility contract. The engine runs fully in simulation
        with zero credentials; keys only enable the live path. The data is synthetic by design
        (Track 3&rsquo;s ask) but <strong>calibrated to real benchmarks</strong>, not invented.
      </p>

      <div className="caps-grid">
        <Cap
          label="Razorpay gateway"
          on={health?.razorpay_live}
          tone="pos"
          value={health?.razorpay_live ? "Live · test mode" : "Mock gateway"}
          note={health?.razorpay_live ? "Creating real test-mode payment links" : "Deterministic offline stand-in"}
        />
        <Cap
          label="Dunning author"
          on={health?.llm_enabled}
          tone="cool"
          value={health?.llm_enabled ? `LLM · ${health.llm_provider}` : "Templates"}
          note={health?.llm_enabled ? "Copy authored live; eval always uses templates" : "Deterministic multilingual templates"}
        />
        <Cap
          label="Models"
          on={health?.models_loaded}
          tone="pos"
          value={health?.models_loaded ? "Loaded" : "Not loaded"}
          note="Recovery-probability + optimal-timing"
        />
        <Cap
          label="Sample episodes"
          on={episodes != null}
          tone="pos"
          value={episodes != null ? episodes.toLocaleString("en-IN") : "—"}
          note="Pre-planned cases for the console"
        />
      </div>

      <div className="page__cols">
        <Card className="panel">
          <div className="panel__head">
            <h2>Held-out evaluation</h2>
            <Pill tone="neutral">frozen</Pill>
          </div>
          <div className="kv">
            <div className="kv__row"><span>Customers</span><span className="tnum">{(hd.customers ?? 6000).toLocaleString("en-IN")}</span></div>
            <div className="kv__row"><span>Failed charges</span><span className="tnum">{(hd.failures ?? 9000).toLocaleString("en-IN")}</span></div>
            <div className="kv__row"><span>Holdout seed</span><span className="mono">{hd.seed ?? 9999}</span></div>
            <div className="kv__row"><span>Triage AUC</span><span className="tnum">{(metrics?.holdout?.engine_prediction_auc ?? 0.6644).toFixed(4)}</span></div>
          </div>
        </Card>

        <Card className="panel">
          <div className="panel__head">
            <h2>Reproducibility</h2>
            <Pill tone="pos" icon>deterministic</Pill>
          </div>
          <ul className="repro">
            <li><Icon name="check" size={15} /> Training seed 7, holdout seed 9999 — disjoint populations</li>
            <li><Icon name="check" size={15} /> Every policy faces identical hidden latents</li>
            <li><Icon name="check" size={15} /> ML &amp; policy never import the ground-truth environment</li>
            <li><Icon name="check" size={15} /> Reproduce with <span className="mono">make eval</span></li>
          </ul>
        </Card>
      </div>

      <Card className="panel">
        <div className="panel__head">
          <h2>Calibrated to reality</h2>
          <Pill tone="cool">synthetic · benchmark-tuned</Pill>
        </div>
        <ul className="repro repro--cols">
          <li><Icon name="check" size={15} /> 20–40% involuntary-churn rate — the documented range for recurring businesses</li>
          <li><Icon name="check" size={15} /> Failure-reason mix modelled on real card / UPI-autopay / e-mandate decline taxonomies</li>
          <li><Icon name="check" size={15} /> Salary-day balance troughs &amp; issuer soft-decline patterns reflect Indian retail behaviour</li>
          <li><Icon name="check" size={15} /> Amounts, tenures &amp; the 8-language / multi-city spread drawn from realistic distributions</li>
        </ul>
      </Card>
    </div>
  );
}
