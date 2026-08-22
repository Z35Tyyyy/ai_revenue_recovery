import React, { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Card, Pill, Meter, Icon, Button, CLASS_TONE } from "../components/ui.jsx";
import { formatINR } from "../api.js";
import { classLabel, actionLabel } from "../lib/labels.js";

const SCENARIOS = [
  { k: "balanced", label: "Balanced book" },
  { k: "expired_cards", label: "Expired-card wave" },
  { k: "insufficient_funds", label: "Payday crunch" },
  { k: "mandate_issues", label: "Mandate lapses" },
  { k: "hard_declines", label: "Fraud spike" },
];

const EMPTY = { n: 0, rate: 0, revenue_paise: 0, retries: 0 };

export function Live() {
  const [scenario, setScenario] = useState("balanced");
  const [n, setN] = useState(120);
  const [running, setRunning] = useState(false);
  const [done, setDone] = useState(false);
  const [progress, setProgress] = useState(0);
  const [eng, setEng] = useState(EMPTY);
  const [base, setBase] = useState(EMPTY);
  const [feed, setFeed] = useState([]);
  const [error, setError] = useState(null);
  const esRef = useRef(null);

  const stop = () => {
    esRef.current?.close();
    esRef.current = null;
  };
  useEffect(() => () => stop(), []);

  // Auto-start a campaign the moment the page opens so a first-time visitor sees the
  // engine actually running — never a cold, all-zero screen. ?scenario= overrides.
  const autoRan = useRef(false);
  useEffect(() => {
    if (autoRan.current) return;
    autoRan.current = true;
    const p = new URLSearchParams(window.location.search);
    setTimeout(() => run(p.get("scenario") || "balanced"), 200);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const run = (sc = scenario, count = n) => {
    stop();
    setScenario(sc);
    setN(count);
    setRunning(true);
    setDone(false);
    setError(null);
    setProgress(0);
    setEng(EMPTY);
    setBase(EMPTY);
    setFeed([]);
    const es = new EventSource(`/api/campaign/stream?n=${count}&scenario=${sc}`);
    esRef.current = es;
    es.onmessage = (e) => {
      const ev = JSON.parse(e.data);
      if (ev.type === "case") {
        setEng(ev.totals.engine);
        setBase(ev.totals.baseline);
        setProgress(ev.i + 1);
        setFeed((f) => [{ ...ev.case, e: ev.engine.recovered, b: ev.baseline.recovered, action: ev.engine.action }, ...f].slice(0, 9));
      } else if (ev.type === "done") {
        setRunning(false);
        setDone(true);
        stop();
      }
    };
    es.onerror = () => {
      setError("Stream disconnected — is the API running on :8000?");
      setRunning(false);
      stop();
    };
  };

  const upliftPts = ((eng.rate || 0) - (base.rate || 0)) * 100;
  const pct = n ? Math.min(100, (progress / n) * 100) : 0;

  return (
    <div className="page live">
      <p className="page__lead">
        Watch the engine actually <strong>run</strong> — a fresh stream of failed charges flows
        through it (with a bandit learning live) racing the Razorpay fixed-retry default on the
        same hidden ground truth. Reshape the failure world below and watch the policy react.
      </p>

      <Card className="live__controls">
        <div className="live__scenarios">
          {SCENARIOS.map((s) => (
            <button
              key={s.k}
              className={`chip ${scenario === s.k ? "is-active" : ""}`}
              disabled={running}
              onClick={() => setScenario(s.k)}
            >
              {s.label}
            </button>
          ))}
        </div>
        <div className="live__run">
          <label className="live__vol">
            <span className="mono">{n} charges</span>
            <input type="range" min="40" max="300" step="20" value={n} disabled={running}
              onChange={(e) => setN(Number(e.target.value))} />
          </label>
          <Button variant="primary" onClick={run} disabled={running}>
            {running ? "Running…" : done ? "Run again" : "Run live"} <Icon name="bolt" size={15} />
          </Button>
        </div>
      </Card>

      {error && <p className="agent__error">{error}</p>}

      {/* live progress */}
      <div className="live__progress">
        <Meter value={pct / 100} tone="cool" height={4} animated={false} />
        <span className="mono live__progress-txt">{progress} / {n} processed</span>
      </div>

      {/* the race */}
      <div className="live__race">
        <Card className="race race--engine" glow>
          <div className="race__head">
            <span className="race__name">AI Revenue Recovery</span>
            <Pill tone="pos" icon>engine</Pill>
          </div>
          <div className="race__rate tnum">{(eng.rate * 100).toFixed(1)}%</div>
          <Meter value={eng.rate} tone="pos" height={8} animated={false} />
          <div className="race__stats">
            <span>{formatINR(eng.revenue_paise)} recovered</span>
            <span className="mono">{eng.retries?.toLocaleString("en-IN")} retries</span>
          </div>
        </Card>

        <div className="race__vs">
          <div className={`race__uplift ${upliftPts >= 0 ? "is-pos" : "is-neg"}`}>
            {upliftPts >= 0 ? "+" : ""}{upliftPts.toFixed(1)}
            <span>pts</span>
          </div>
          <span className="race__vs-lab mono">uplift</span>
        </div>

        <Card className="race race--base">
          <div className="race__head">
            <span className="race__name">Fixed retry</span>
            <Pill tone="neutral">Razorpay default</Pill>
          </div>
          <div className="race__rate tnum race__rate--muted">{(base.rate * 100).toFixed(1)}%</div>
          <Meter value={base.rate} tone="neutral" height={8} animated={false} />
          <div className="race__stats">
            <span>{formatINR(base.revenue_paise)} recovered</span>
            <span className="mono">{base.retries?.toLocaleString("en-IN")} retries</span>
          </div>
        </Card>
      </div>

      {/* live case feed */}
      <div className="panel__head panel__head--loose">
        <h2>Live decisions</h2>
        <span className="panel__legend">
          <span className="dot dot--pos" /> engine <span className="dot dot--muted" /> fixed retry
        </span>
      </div>
      <Card className="live__feed">
        {feed.length === 0 && (
          <div className="live__feed-empty mono">
            {running ? "streaming failed charges…" : "starting a live campaign…"}
          </div>
        )}
        <AnimatePresence initial={false}>
          {feed.map((c) => (
            <motion.div
              key={c.id}
              layout
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="lrow"
            >
              <span className="lrow__reason mono">{c.reason}</span>
              <Pill tone={CLASS_TONE[c.class] || "neutral"}>{classLabel(c.class)}</Pill>
              <span className="lrow__amt tnum">{c.amount}</span>
              <span className="lrow__act">{actionLabel(c.action)}</span>
              <span className={`lrow__out ${c.e ? "is-win" : "is-loss"}`}>
                {c.e ? <Icon name="check" size={13} /> : <Icon name="close" size={12} />} engine
              </span>
              <span className={`lrow__out lrow__out--base ${c.b ? "is-win" : "is-loss"}`}>
                {c.b ? <Icon name="check" size={13} /> : <Icon name="close" size={12} />} fixed
              </span>
            </motion.div>
          ))}
        </AnimatePresence>
      </Card>
    </div>
  );
}
