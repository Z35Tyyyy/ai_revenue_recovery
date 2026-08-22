import React, { useMemo } from "react";
import { motion } from "framer-motion";
import { Card, Pill, Icon, Reveal, fadeUp, stagger, CLASS_TONE } from "../components/ui.jsx";
import { useCases } from "../lib/useData.js";
import { formatINR } from "../api.js";
import { classLabel } from "../lib/labels.js";

// Honest, plain-English reason each class can't (yet) be recovered — and the
// stopping rule the agent applied.
const WHY = {
  hard_decline: {
    title: "Dead instrument",
    why: "Stolen, invalid, or frozen — there's no card left to charge. Retrying only burns bank fees, so the agent stops on the first look.",
    rule: "Stopped: ML triage P(recover) below the give-up floor.",
  },
  needs_reauth: {
    title: "Mandate needs re-authorisation",
    why: "The UPI-autopay / e-mandate was revoked or paused — by rule, only the customer can re-authorise. The agent sent the re-auth request; recovery now needs their tap.",
    rule: "Handed off: requires customer re-authorisation (compliant).",
  },
  needs_card_update: {
    title: "Card needs updating",
    why: "The card expired or was blocked for recurring use. The agent asked the customer for a fresh card; the charge is pending their update.",
    rule: "Handed off: awaiting a new payment method.",
  },
  insufficient_funds: {
    title: "Funds never arrived",
    why: "Even timed to the salary window, the balance stayed short across the whole retry horizon. The agent exhausted its smart retries.",
    rule: "Stopped: retry horizon exhausted.",
  },
  soft_decline: {
    title: "Issuer kept declining",
    why: "The bank soft-declined every attempt across the retry window with no path to succeed.",
    rule: "Stopped: retry horizon exhausted.",
  },
  transient: {
    title: "Persisted past the glitch",
    why: "Treated as a temporary issuer/gateway blip, but it never cleared within the window.",
    rule: "Stopped: retry horizon exhausted.",
  },
};

export function Exceptions() {
  const { cases, loading } = useCases({ limit: 200 });

  const { groups, count, revenue } = useMemo(() => {
    const rows = (cases || []).filter((c) => !c.recovered);
    const by = {};
    let rev = 0;
    for (const c of rows) {
      const k = c.class || "unknown";
      by[k] = by[k] || { klass: k, count: 0, revenue: 0, reasons: new Set(), gaveUp: 0 };
      by[k].count += 1;
      by[k].revenue += c.amount_paise || 0;
      by[k].reasons.add(c.reason);
      if (c.status === "gave_up") by[k].gaveUp += 1;
      rev += c.amount_paise || 0;
    }
    const groups = Object.values(by)
      .map((g) => ({ ...g, reasons: [...g.reasons].slice(0, 4) }))
      .sort((a, b) => b.revenue - a.revenue);
    return { groups, count: rows.length, revenue: rev };
  }, [cases]);

  if (loading) return <div className="dash__loading mono">loading…</div>;

  return (
    <div className="page">
      <p className="page__lead">
        The agent doesn't pretend. Of the batch it worked, <strong>{count}</strong> charges (
        <strong>{formatINR(revenue)}</strong>) it could <em>not</em> recover — grouped below with an
        honest reason and the stopping rule it applied. Knowing when to stop wasting retries is part
        of the job.
      </p>

      <motion.div
        className="exc"
        variants={stagger(0.06)}
        initial="hidden"
        animate="show"
      >
        {groups.length === 0 && (
          <Reveal className="card exc__none" variants={fadeUp}>
            Nothing unresolved in this batch.
          </Reveal>
        )}
        {groups.map((g) => {
          const meta = WHY[g.klass] || { title: classLabel(g.klass), why: "", rule: "" };
          return (
            <motion.div key={g.klass} className="exc__card card" variants={fadeUp}>
              <div className="exc__head">
                <div>
                  <div className="exc__title">{meta.title}</div>
                  <Pill tone={CLASS_TONE[g.klass] || "neutral"}>{classLabel(g.klass)}</Pill>
                </div>
                <div className="exc__stat">
                  <div className="exc__count tnum">{g.count}</div>
                  <div className="exc__rev tnum">{formatINR(g.revenue)}</div>
                </div>
              </div>
              <p className="exc__why">{meta.why}</p>
              <div className="exc__reasons">
                {g.reasons.map((r) => (
                  <span key={r} className="exc__reason mono">{r}</span>
                ))}
              </div>
              <div className="exc__rule">
                <Icon name="bolt" size={13} /> {meta.rule}
              </div>
            </motion.div>
          );
        })}
      </motion.div>
    </div>
  );
}
