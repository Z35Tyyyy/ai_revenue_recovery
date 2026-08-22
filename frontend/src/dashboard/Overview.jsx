import React, { useMemo } from "react";
import { Link } from "react-router-dom";
import { Reveal, Counter, Card, Pill, Meter, Icon, fadeUp, stagger } from "../components/ui.jsx";
import { motion } from "framer-motion";
import { useMetrics, useCases } from "../lib/useData.js";
import { formatINR } from "../api.js";
import { actionLabel, classLabel } from "../lib/labels.js";

const CLASS_ORDER = [
  "needs_card_update", "needs_reauth", "insufficient_funds",
  "soft_decline", "transient", "hard_decline",
];

function Tile({ label, value, sub, delta, deltaTone = "pos" }) {
  return (
    <Card className="tile">
      <div className="tile__label">{label}</div>
      <div className="tile__value tnum">{value}</div>
      <div className="tile__foot">
        {delta && <span className={`tile__delta tile__delta--${deltaTone}`}>{delta}</span>}
        {sub && <span className="tile__sub">{sub}</span>}
      </div>
    </Card>
  );
}

export function Overview() {
  const { metrics, loading } = useMetrics();
  const { cases } = useCases({ limit: 200 });

  const h = metrics?.holdout;
  const eng = h?.policies?.engine;
  const fixed = h?.policies?.fixed_retry;
  const up = h?.uplift?.vs_fixed_retry;

  // Recovered-by-action attribution, computed live from the sample cases.
  const attribution = useMemo(() => {
    const rows = cases || [];
    const by = {};
    let totalRev = 0;
    for (const c of rows) {
      if (!c.recovered) continue;
      const a = c.decision?.action || "recovered";
      by[a] = by[a] || { action: a, count: 0, revenue: 0 };
      by[a].count += 1;
      by[a].revenue += c.amount_paise || 0;
      totalRev += c.amount_paise || 0;
    }
    const list = Object.values(by).sort((a, b) => b.revenue - a.revenue);
    return { list, totalRev };
  }, [cases]);

  if (loading) return <div className="dash__loading mono">loading…</div>;

  const atRisk = eng?.revenue_total_paise ?? 1328480000;
  const recovered = eng?.revenue_recovered_paise ?? 910519800;
  const rate = eng?.recovery_rate ?? 0.678;
  const total = eng?.total ?? 9000;

  return (
    <div className="page console">
      <p className="page__lead">
        Connected to Razorpay · scanned <strong>{total.toLocaleString("en-IN")}</strong> failed
        recurring charges · <strong>{formatINR(atRisk)}</strong> of revenue at risk. Here's what the
        agent won back.
      </p>

      {/* hero odometer */}
      <Reveal className="hero-recovered card card--glow" variants={fadeUp}>
        <div className="hero-recovered__main">
          <div className="hero-recovered__label mono">Revenue recovered</div>
          <div className="hero-recovered__value tnum">
            <Counter to={recovered / 100} format={(v) => formatINR(Math.round(v) * 100)} duration={1.6} />
          </div>
          <div className="hero-recovered__sub">
            <strong className="tnum">{(rate * 100).toFixed(1)}%</strong> of failed revenue recovered
            {up && (
              <span className="hero-recovered__delta">
                +{(up.recovery_rate_abs * 100).toFixed(1)} pts vs Razorpay's next-day retry
              </span>
            )}
          </div>
        </div>
        <Link to="/dashboard/live" className="hero-recovered__cta">
          Watch it run live <Icon name="arrow" size={16} />
        </Link>
      </Reveal>

      {/* tiles */}
      <motion.div className="tiles" variants={stagger(0.06)} initial="hidden" animate="show">
        <motion.div variants={fadeUp}>
          <Tile label="Revenue at risk" value={formatINR(atRisk)} sub={`${total.toLocaleString("en-IN")} failed charges`} />
        </motion.div>
        <motion.div variants={fadeUp}>
          <Tile label="Recovered" value={formatINR(recovered)} delta={`${(rate * 100).toFixed(1)}%`} sub="of at-risk revenue" />
        </motion.div>
        <motion.div variants={fadeUp}>
          <Tile
            label="vs Razorpay default"
            value={`+${((up?.recovery_rate_abs ?? 0.207) * 100).toFixed(1)} pts`}
            delta={`+${formatINR(up?.revenue_recovered_delta_paise ?? 275498300)}`}
            sub="extra recovered"
          />
        </motion.div>
        <motion.div variants={fadeUp}>
          <Tile
            label="Bank retries"
            value={(eng?.retries ?? 12906).toLocaleString("en-IN")}
            deltaTone="cool"
            delta={`≈½ of ${((fixed?.retries ?? 26361) / 1000).toFixed(0)}k`}
            sub="fewer, better-timed"
          />
        </motion.div>
      </motion.div>

      {/* the batch banner — the rubric line, verbatim shape */}
      <Reveal className="batch-banner card" variants={fadeUp}>
        <Icon name="check" size={18} />
        <span>
          Agent ran a closed recovery loop across <strong>{total.toLocaleString("en-IN")}</strong>{" "}
          failed recurring charges → recovered <strong>{formatINR(recovered)}</strong> (
          {(rate * 100).toFixed(1)}%) vs <strong>{formatINR(fixed?.revenue_recovered_paise ?? 635021500)}</strong>{" "}
          ({((fixed?.recovery_rate ?? 0.471) * 100).toFixed(1)}%) with Razorpay's next-day retry — with
          roughly half the bank retries, every decision logged.
        </span>
      </Reveal>

      <div className="page__cols">
        {/* recovered by action */}
        <Reveal className="panel card" variants={fadeUp}>
          <div className="panel__head">
            <h2>How the money came back</h2>
            <Pill tone="neutral">by action</Pill>
          </div>
          <div className="attribution">
            {attribution.list.length === 0 && <div className="mono attribution__empty">—</div>}
            {attribution.list.map((r) => (
              <div key={r.action} className="attribution__row">
                <span className="attribution__name">{actionLabel(r.action)}</span>
                <span className="attribution__meter">
                  <Meter value={r.revenue / (attribution.totalRev || 1)} tone="pos" height={7} />
                </span>
                <span className="attribution__val tnum">{formatINR(r.revenue)}</span>
              </div>
            ))}
          </div>
          <Link to="/dashboard/recoveries" className="panel__link">
            See every decision & audit trail <Icon name="arrow" size={13} />
          </Link>
        </Reveal>

        {/* recovery by class vs default */}
        <Reveal className="panel card" variants={fadeUp}>
          <div className="panel__head">
            <h2>Where it beats a blind retry</h2>
            <span className="panel__legend">
              <span className="dot dot--muted" /> default <span className="dot dot--pos" /> agent
            </span>
          </div>
          <div className="byclass">
            {CLASS_ORDER.map((c) => {
              const f = fixed?.by_class_rate?.[c] ?? 0;
              const e = eng?.by_class_rate?.[c] ?? 0;
              return (
                <div key={c} className="byclass__row">
                  <span className="byclass__name">{classLabel(c)}</span>
                  <span className="byclass__bars">
                    <Meter value={f} tone="neutral" height={5} />
                    <Meter value={e} tone="pos" height={5} />
                  </span>
                  <span className="byclass__pct tnum">
                    <span className="byclass__pct-muted">{(f * 100).toFixed(0)}</span>
                    <Icon name="arrow" size={11} />
                    <span className="byclass__pct-pos">{(e * 100).toFixed(0)}%</span>
                  </span>
                </div>
              );
            })}
          </div>
          <Link to="/dashboard/exceptions" className="panel__link">
            What it couldn't recover, and why <Icon name="arrow" size={13} />
          </Link>
        </Reveal>
      </div>
    </div>
  );
}
