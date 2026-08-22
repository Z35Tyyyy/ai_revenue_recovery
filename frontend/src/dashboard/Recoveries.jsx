import React, { useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Pill, Icon, Meter, CLASS_TONE, STATUS_TONE, ACTION_TONE } from "../components/ui.jsx";
import { useCases } from "../lib/useData.js";
import { formatINR } from "../api.js";
import { classLabel, actionLabel } from "../lib/labels.js";

const STATUS_LABEL = { recovered: "recovered", halted: "halted", open: "open", gave_up: "gave up" };

function StatusDot({ recovered, status }) {
  const tone = recovered ? "pos" : STATUS_TONE[status] || "neutral";
  return <span className={`sdot sdot--${tone}`} aria-hidden="true" />;
}

function Row({ c, onOpen }) {
  const ref = useRef(null);
  return (
    <div
      ref={ref}
      className="rec__row"
      role="button"
      tabIndex={0}
      aria-label={`${classLabel(c.class)} · ${formatINR(c.amount_paise)} · ${c.recovered ? "recovered" : c.status}`}
      onClick={() => onOpen(c, ref)}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onOpen(c, ref);
        }
      }}
    >
      <span className="rec__cell rec__status">
        <StatusDot recovered={c.recovered} status={c.status} />
      </span>
      <span className="rec__cell rec__reason">
        <span className="rec__reason-main mono">{c.reason}</span>
        <span className="rec__reason-id mono">{c.id}</span>
      </span>
      <span className="rec__cell">
        <Pill tone={CLASS_TONE[c.class] || "neutral"}>{classLabel(c.class)}</Pill>
      </span>
      <span className="rec__cell rec__cust mono">
        {c.customer?.city} · {c.customer?.language}
      </span>
      <span className="rec__cell rec__amount tnum">{formatINR(c.amount_paise)}</span>
      <span className="rec__cell rec__action">
        {c.decision ? (
          <span className={`rec__action-tag rec__action-tag--${ACTION_TONE[c.decision.action] || "neutral"}`}>
            {actionLabel(c.decision.action)}
          </span>
        ) : (
          <span className="rec__action-tag rec__action-tag--neg">stopped</span>
        )}
      </span>
      <span className="rec__cell rec__chev">
        <Icon name="arrow" size={14} />
      </span>
    </div>
  );
}

function Drawer({ c, onClose }) {
  const panelRef = useRef(null);
  useEffect(() => {
    panelRef.current?.focus();
    const onKey = (e) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = prev;
    };
  }, [onClose]);

  return (
    <motion.div
      className="drawer__scrim"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      onClick={onClose}
    >
      <motion.aside
        className="drawer card"
        role="dialog"
        aria-modal="true"
        aria-label={`Recovery ${c.id}`}
        tabIndex={-1}
        ref={panelRef}
        initial={{ x: 40, opacity: 0 }}
        animate={{ x: 0, opacity: 1 }}
        exit={{ x: 40, opacity: 0 }}
        transition={{ duration: 0.28, ease: [0.22, 1, 0.36, 1] }}
        onClick={(e) => e.stopPropagation()}
      >
        <header className="drawer__head">
          <div>
            <div className="drawer__eyebrow mono">{c.reason}</div>
            <h2>{classLabel(c.class)}</h2>
          </div>
          <button className="drawer__close" onClick={onClose} aria-label="Close">
            <Icon name="close" size={18} />
          </button>
        </header>

        <div className="drawer__facts">
          <div className="fact">
            <span className="fact__k">Amount</span>
            <span className="fact__v tnum">{formatINR(c.amount_paise)}</span>
          </div>
          <div className="fact">
            <span className="fact__k">Outcome</span>
            <span className="fact__v">
              <Pill tone={c.recovered ? "pos" : STATUS_TONE[c.status] || "neutral"}>
                {c.recovered ? "recovered" : STATUS_LABEL[c.status] || c.status}
              </Pill>
            </span>
          </div>
          <div className="fact">
            <span className="fact__k">Triage P(recover)</span>
            <span className="fact__v tnum">{((c.predicted_recover_prob ?? 0) * 100).toFixed(0)}%</span>
          </div>
          <div className="fact">
            <span className="fact__k">Customer</span>
            <span className="fact__v mono">
              {c.customer?.city} · {c.customer?.language} · {c.customer?.tenure_months}mo
            </span>
          </div>
        </div>

        {c.decision && (
          <div className="drawer__decision">
            <span className="drawer__decision-lab">Chose</span>
            <span className={`rec__action-tag rec__action-tag--${ACTION_TONE[c.decision.action] || "neutral"}`}>
              {actionLabel(c.decision.action)}
            </span>
            {c.decision.prob != null && (
              <span className="drawer__decision-p tnum">P={(c.decision.prob * 100).toFixed(0)}%</span>
            )}
          </div>
        )}

        {c.candidates?.length > 0 && (
          <section className="drawer__section">
            <h3>Considered</h3>
            <div className="cands">
              {c.candidates.map((cand, i) => (
                <div key={i} className={`cand ${cand.action === c.decision?.action ? "cand--win" : ""}`}>
                  <span className="cand__name">{actionLabel(cand.action)}</span>
                  <Meter value={cand.prob} tone={cand.action === c.decision?.action ? "pos" : "neutral"} height={5} />
                  <span className="cand__p tnum">{(cand.prob * 100).toFixed(0)}%</span>
                </div>
              ))}
            </div>
          </section>
        )}

        <section className="drawer__section">
          <h3>Reasoning trace</h3>
          <ol className="trace">
            {c.trace?.map((t, i) => (
              <li key={i} className="trace__line">
                <span className="trace__n mono">{String(i + 1).padStart(2, "0")}</span>
                <span className="trace__t">{t}</span>
              </li>
            ))}
          </ol>
        </section>
      </motion.aside>
    </motion.div>
  );
}

const FILTERS = [
  { k: "all", label: "All" },
  { k: "recovered", label: "Recovered" },
  { k: "open", label: "In progress" },
  { k: "gave_up", label: "Stopped" },
];

export function Recoveries() {
  const { cases, total, live, loading } = useCases({ limit: 200 });
  const [filter, setFilter] = useState("all");
  const [q, setQ] = useState("");
  const [selected, setSelected] = useState(null);
  const triggerRef = useRef(null);

  const open = (c, ref) => {
    triggerRef.current = ref?.current || null;
    setSelected(c);
  };
  const close = () => {
    setSelected(null);
    triggerRef.current?.focus();
  };

  const rows = useMemo(() => {
    let r = cases || [];
    if (filter === "recovered") r = r.filter((c) => c.recovered);
    else if (filter === "open") r = r.filter((c) => !c.recovered && c.status !== "gave_up");
    else if (filter === "gave_up") r = r.filter((c) => c.status === "gave_up");
    if (q.trim()) {
      const s = q.toLowerCase();
      r = r.filter((c) => c.reason.toLowerCase().includes(s) || c.id.toLowerCase().includes(s) || classLabel(c.class).toLowerCase().includes(s));
    }
    return r;
  }, [cases, filter, q]);

  if (loading) return <div className="dash__loading mono">loading cases…</div>;

  return (
    <div className="page">
      <p className="page__lead">
        Every decision the engine made, as an explainable log — click a row for the full reasoning
        trace. {!live && <span className="page__note">Showing sample episodes (API offline).</span>}
      </p>

      <div className="rec__toolbar">
        <div className="chips" role="tablist" aria-label="Filter recoveries">
          {FILTERS.map((f) => (
            <button
              key={f.k}
              role="tab"
              aria-selected={filter === f.k}
              className={`chip ${filter === f.k ? "is-active" : ""}`}
              onClick={() => setFilter(f.k)}
            >
              {f.label}
            </button>
          ))}
        </div>
        <input
          className="rec__search"
          placeholder="Search reason, class, id…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          aria-label="Search recoveries"
        />
      </div>

      <div className="rec card">
        <div className="rec__row rec__row--head" aria-hidden="true">
          <span className="rec__cell" />
          <span className="rec__cell">Failure</span>
          <span className="rec__cell">Class</span>
          <span className="rec__cell">Customer</span>
          <span className="rec__cell rec__amount">Amount</span>
          <span className="rec__cell">Decision</span>
          <span className="rec__cell" />
        </div>
        {rows.length === 0 && <div className="rec__empty mono">no cases match</div>}
        {rows.map((c) => (
          <Row key={c.id} c={c} onOpen={open} />
        ))}
      </div>
      <div className="rec__count mono">
        {rows.length} of {total} cases
      </div>

      <AnimatePresence>{selected && <Drawer c={selected} onClose={close} />}</AnimatePresence>
    </div>
  );
}
