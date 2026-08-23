import React, { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Card, Pill, Meter, Icon, Button, CLASS_TONE } from "../components/ui.jsx";
import { formatINR } from "../api.js";
import { classLabel, actionLabel } from "../lib/labels.js";
import { LiveFlow } from "./LiveFlow.jsx";

const EMPTY_FLOW = { n: 0, cls: {}, act: {}, ca: {}, ao: {}, won: 0, lost: 0, active: null };

// Auto-play walks every failure world on its own so the graph shows the full
// complexity without anyone selecting scenarios by hand.
const SCEN_CYCLE = ["balanced", "insufficient_funds", "expired_cards", "mandate_issues", "hard_declines"];

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
  const [flow, setFlow] = useState(EMPTY_FLOW);
  const [error, setError] = useState(null);
  const [auto, setAuto] = useState(true);
  const esRef = useRef(null);
  const autoRef = useRef(true);
  const cycleRef = useRef(0);
  const nextTimer = useRef(null);

  const stop = () => {
    esRef.current?.close();
    esRef.current = null;
    if (nextTimer.current) { clearTimeout(nextTimer.current); nextTimer.current = null; }
  };
  useEffect(() => () => { autoRef.current = false; stop(); }, []);

  const startAuto = () => {
    autoRef.current = true;
    setAuto(true);
    run(SCEN_CYCLE[cycleRef.current], n, true);
  };
  const stopAuto = () => {
    autoRef.current = false;
    setAuto(false);
  };

  // Auto-play the moment the page opens: walk every failure world on a loop, so a
  // first-time visitor sees the full complexity build up with zero clicking.
  const autoRan = useRef(false);
  useEffect(() => {
    if (autoRan.current) return;
    autoRan.current = true;
    const p = new URLSearchParams(window.location.search);
    const start = p.get("scenario");
    if (start && SCEN_CYCLE.includes(start)) cycleRef.current = SCEN_CYCLE.indexOf(start);
    const single = p.get("auto") === "0"; // ?auto=0 → run one world, don't loop
    autoRef.current = !single;
    if (single) setAuto(false);
    setTimeout(() => run(SCEN_CYCLE[cycleRef.current], n, !single), 200);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const run = (sc = scenario, count = n, isAuto = false) => {
    if (!isAuto) { autoRef.current = false; setAuto(false); }
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
    setFlow(EMPTY_FLOW);
    const es = new EventSource(`/api/campaign/stream?n=${count}&scenario=${sc}`);
    esRef.current = es;
    es.onmessage = (e) => {
      const ev = JSON.parse(e.data);
      if (ev.type === "case") {
        setEng(ev.totals.engine);
        setBase(ev.totals.baseline);
        setProgress(ev.i + 1);
        setFeed((f) => [{ ...ev.case, e: ev.engine.recovered, b: ev.baseline.recovered, action: ev.engine.action }, ...f].slice(0, 9));
        const cls = ev.case.class, actn = ev.engine.action, out = ev.engine.recovered ? "won" : "lost";
        setFlow((f) => ({
          n: f.n + 1,
          cls: { ...f.cls, [cls]: (f.cls[cls] || 0) + 1 },
          act: { ...f.act, [actn]: (f.act[actn] || 0) + 1 },
          ca: { ...f.ca, [`${cls}>${actn}`]: (f.ca[`${cls}>${actn}`] || 0) + 1 },
          ao: { ...f.ao, [`${actn}>${out}`]: (f.ao[`${actn}>${out}`] || 0) + 1 },
          won: f.won + (out === "won" ? 1 : 0),
          lost: f.lost + (out === "won" ? 0 : 1),
          active: { cls, act: actn, out },
        }));
      } else if (ev.type === "done") {
        setRunning(false);
        setDone(true);
        stop();
        if (autoRef.current) {
          cycleRef.current = (cycleRef.current + 1) % SCEN_CYCLE.length;
          nextTimer.current = setTimeout(() => {
            if (autoRef.current) run(SCEN_CYCLE[cycleRef.current], count, true);
          }, 1100);
        }
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
        Watch the engine actually <strong>run</strong> — failed charges stream through it (with a
        bandit learning live) racing the Razorpay fixed-retry default on the same hidden ground
        truth. <strong>Auto-play</strong> cycles through every failure world on its own; the flow
        graph below redraws itself as the policy adapts. Pick a world to take over.
      </p>

      <Card className="live__controls">
        <div className="live__scenarios">
          <button
            className={`chip chip--auto ${auto ? "is-active" : ""}`}
            onClick={() => (auto ? stopAuto() : startAuto())}
            title="Cycle through every failure world automatically"
          >
            {auto ? "◉" : "○"} Auto-play
          </button>
          {SCENARIOS.map((s) => (
            <button
              key={s.k}
              className={`chip ${scenario === s.k ? "is-active" : ""}`}
              onClick={() => run(s.k, n, false)}
            >
              {s.label}
            </button>
          ))}
        </div>
        <div className="live__run">
          <label className="live__vol">
            <span className="mono">{n} charges</span>
            <input type="range" min="40" max="300" step="20" value={n}
              onChange={(e) => setN(Number(e.target.value))} />
          </label>
          <Button variant="primary" onClick={() => run(scenario, n, false)} disabled={running && !auto}>
            {auto ? "Auto-playing…" : running ? "Running…" : done ? "Run again" : "Run once"} <Icon name="bolt" size={15} />
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

      {/* growing recovery-flow graph — each payment routes failure → move → outcome */}
      <div className="panel__head panel__head--loose">
        <h2>Recovery flow</h2>
        <span className="panel__legend mono">
          {auto && <span className="live__world">↻ {SCENARIOS.find((s) => s.k === scenario)?.label}</span>}
          {flow.n > 0 ? ` ${flow.n} routed` : " builds as it runs"}
        </span>
      </div>
      <Card className="live__flow-card">
        <LiveFlow flow={flow} />
      </Card>

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
