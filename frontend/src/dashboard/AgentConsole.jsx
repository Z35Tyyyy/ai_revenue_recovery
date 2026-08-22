import React, { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Button, Pill, Meter, Icon, Card, CLASS_TONE, ACTION_TONE } from "../components/ui.jsx";
import { useReasons, useHealth } from "../lib/useData.js";
import { api, formatINR } from "../api.js";
import { classLabel, actionLabel } from "../lib/labels.js";

const LANGS = [
  ["hinglish", "Hinglish"], ["hi", "हिन्दी"], ["en", "English"],
  ["ta", "தமிழ்"], ["te", "తెలుగు"], ["bn", "বাংলা"], ["mr", "मराठी"], ["kn", "ಕನ್ನಡ"],
];
const CHANNELS = [["whatsapp", "WhatsApp"], ["sms", "SMS"], ["email", "Email"]];
const METHODS = [
  ["card", "Card"], ["upi_autopay", "UPI-autopay"], ["emandate", "e-Mandate"],
  ["netbanking", "Netbanking"], ["wallet", "Wallet"],
];

const DEFAULTS = {
  reason_code: "card_expired",
  amount_rupees: 499,
  method: "card",
  language: "hinglish",
  preferred_channel: "whatsapp",
  city: "Mumbai",
  tenure_months: 12,
  salary_day: 1,
  create_payment_link: false,
};

function Field({ label, children, hint }) {
  return (
    <label className="field">
      <span className="field__label">{label}</span>
      {children}
      {hint && <span className="field__hint">{hint}</span>}
    </label>
  );
}

export function AgentConsole() {
  const reasons = useReasons();
  const { health } = useHealth();
  const [form, setForm] = useState(DEFAULTS);
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [ff, setFf] = useState(null);
  const [ffBusy, setFfBusy] = useState(false);
  const ctrlRef = useRef(null);

  const fastForward = async () => {
    setFfBusy(true);
    try {
      setFf(await api.advanceClock());
    } catch {
      /* offline */
    } finally {
      setFfBusy(false);
    }
  };

  useEffect(() => () => ctrlRef.current?.abort(), []);

  const set = (k) => (e) => {
    const v = e.target.type === "checkbox" ? e.target.checked : e.target.value;
    setForm((f) => ({ ...f, [k]: v }));
  };

  const run = async () => {
    ctrlRef.current?.abort();
    const ctrl = new AbortController();
    ctrlRef.current = ctrl;
    setBusy(true);
    setError(null);
    try {
      const body = {
        reason_code: form.reason_code,
        amount_paise: Math.round(Number(form.amount_rupees) * 100),
        method: form.method,
        language: form.language,
        preferred_channel: form.preferred_channel,
        city: form.city,
        tenure_months: Number(form.tenure_months),
        salary_day: Number(form.salary_day),
        create_payment_link: form.create_payment_link,
      };
      const res = await api.plan(body, ctrl.signal);
      setResult(res);
    } catch (e) {
      if (e?.name !== "AbortError") setError(e.message || "Plan failed");
    } finally {
      if (ctrlRef.current === ctrl) setBusy(false);
    }
  };

  const reason = reasons.find((r) => r.code === form.reason_code);
  const dunning = result?.message; // { text, language, channel, authored_by }
  const link = result?.payment_link; // { id, short_url, is_mock, amount }

  return (
    <div className="page agent">
      <p className="page__lead">
        Hand the engine a live failed charge. It diagnoses, predicts, decides, and — with keys —
        authors a real recovery.
      </p>

      <div className="agent__grid">
        {/* -------- composer -------- */}
        <Card className="agent__form">
          <div className="agent__form-head">
            <h2>Failed charge</h2>
            {reason && (
              <Pill tone={CLASS_TONE[reason.class] || "neutral"}>{classLabel(reason.class)}</Pill>
            )}
          </div>

          <Field label="Failure reason">
            <select className="input" value={form.reason_code} onChange={set("reason_code")}>
              {reasons.map((r) => (
                <option key={r.code} value={r.code}>
                  {r.code}
                </option>
              ))}
            </select>
          </Field>
          {reason && <p className="agent__reason-desc">{reason.description}</p>}

          <div className="field-grid">
            <Field label="Amount (₹)">
              <input className="input tnum" type="number" min="1" value={form.amount_rupees} onChange={set("amount_rupees")} />
            </Field>
            <Field label="Method">
              <select className="input" value={form.method} onChange={set("method")}>
                {METHODS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
              </select>
            </Field>
            <Field label="Language">
              <select className="input" value={form.language} onChange={set("language")}>
                {LANGS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
              </select>
            </Field>
            <Field label="Channel">
              <select className="input" value={form.preferred_channel} onChange={set("preferred_channel")}>
                {CHANNELS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
              </select>
            </Field>
            <Field label="Tenure (mo)">
              <input className="input tnum" type="number" min="0" value={form.tenure_months} onChange={set("tenure_months")} />
            </Field>
            <Field label="Salary day">
              <input className="input tnum" type="number" min="1" max="31" value={form.salary_day} onChange={set("salary_day")} />
            </Field>
          </div>

          <label className={`toggle ${form.create_payment_link ? "is-on" : ""}`}>
            <input type="checkbox" checked={form.create_payment_link} onChange={set("create_payment_link")} />
            <span className="toggle__track"><span className="toggle__knob" /></span>
            <span className="toggle__text">
              Create real payment link
              {form.create_payment_link && health?.razorpay_live && (
                <span className="toggle__warn">⚠ live — sends SMS/email to the contact</span>
              )}
            </span>
          </label>

          <Button variant="primary" size="lg" onClick={run} disabled={busy} className="agent__go">
            {busy ? "Diagnosing…" : "Diagnose & plan"} <Icon name="bolt" size={16} />
          </Button>
          {error && <p className="agent__error">{error}</p>}

          {result?.schedule?.job_id && (
            <div className="agent__ff">
              <button className="agent__ff-btn" onClick={fastForward} disabled={ffBusy}>
                <Icon name="clock" size={14} /> {ffBusy ? "Advancing…" : "Fast-forward the clock"}
              </button>
              {ff && (
                <span className="agent__ff-res">
                  fired {ff.fired} · <strong className="tnum">{ff.recovered}</strong> recovered ·{" "}
                  {ff.pending} pending
                </span>
              )}
            </div>
          )}
        </Card>

        {/* -------- result -------- */}
        <div className="agent__result">
          <AnimatePresence mode="wait">
            {!result ? (
              <motion.div key="empty" className="agent__empty card" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                <Icon name="spark" size={26} />
                <p>The recommendation, alternatives, reasoning trace and generated message will appear here.</p>
              </motion.div>
            ) : (
              <motion.div key="res" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }} className="agent__res-inner">
                <Card className="agent__verdict" glow>
                  <div className="verdict__top">
                    <span className="verdict__lab">Recommended</span>
                    <Pill tone={CLASS_TONE[result.class] || "neutral"}>{classLabel(result.class)}</Pill>
                  </div>
                  {result.decision ? (
                    <>
                      <div className={`verdict__action verdict__action--${ACTION_TONE[result.decision.action] || "neutral"}`}>
                        {actionLabel(result.decision.action)}
                      </div>
                      <div className="verdict__meta">
                        <span>P(success) <strong className="tnum">{((result.decision.prob ?? 0) * 100).toFixed(0)}%</strong></span>
                        {result.decision.ev_paise != null && (
                          <span>Expected value <strong className="tnum">{formatINR(result.decision.ev_paise)}</strong></span>
                        )}
                        {result.decision.when && (
                          <span>When <strong className="mono">{new Date(result.decision.when).toLocaleString("en-IN", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" })}</strong></span>
                        )}
                      </div>
                      {result.decision.ev_paise != null && (
                        <p className="verdict__note">
                          Expected value = P(success) × (this charge + retained customer LTV) − send cost.
                          It exceeds the charge because a recovery keeps the customer, not just this payment.
                        </p>
                      )}
                    </>
                  ) : (
                    <div className="verdict__action verdict__action--neg">Stop — unrecoverable</div>
                  )}
                </Card>

                {result.schedule && (
                  <Card className="agent__sched">
                    <div className="agent__msg-head">
                      <h3><Icon name="clock" size={15} /> Scheduled &amp; compliance</h3>
                      <Pill tone={result.schedule.allowed ? "pos" : result.schedule.requires_afa ? "warn" : "neg"}>
                        {result.schedule.allowed ? "scheduled" : result.schedule.requires_afa ? "needs AFA" : "blocked"}
                      </Pill>
                    </div>
                    {result.schedule.allowed ? (
                      <p className="agent__sched-when">
                        Fires at{" "}
                        <strong className="mono">
                          {new Date(result.schedule.run_at).toLocaleString("en-IN", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" })}
                        </strong>{" "}
                        (durable job #{result.schedule.job_id})
                      </p>
                    ) : (
                      <p className="agent__sched-block">{result.schedule.reason}</p>
                    )}
                    {result.schedule.notes?.map((n, i) => (
                      <p key={i} className="agent__sched-note">⚖ {n}</p>
                    ))}
                  </Card>
                )}

                {result.candidates?.length > 0 && (
                  <Card className="agent__cands">
                    <h3>Alternatives considered</h3>
                    {result.candidates.map((c, i) => (
                      <div key={i} className={`cand ${c.action === result.decision?.action ? "cand--win" : ""}`}>
                        <span className="cand__name">{actionLabel(c.action)}</span>
                        <Meter value={c.prob} tone={c.action === result.decision?.action ? "pos" : "neutral"} height={5} />
                        <span className="cand__p tnum">{(c.prob * 100).toFixed(0)}%</span>
                      </div>
                    ))}
                  </Card>
                )}

                {(dunning || link) && (
                  <Card className="agent__msg">
                    <div className="agent__msg-head">
                      <h3><Icon name="message" size={15} /> Authored message</h3>
                      {dunning?.authored_by && <Pill tone="cool">{dunning.authored_by}</Pill>}
                    </div>
                    {dunning?.text && <p className="agent__msg-body">{dunning.text}</p>}
                    {link?.short_url && (
                      <a className="agent__msg-link" href={link.short_url} target="_blank" rel="noreferrer">
                        <Icon name="link" size={14} /> {link.short_url}
                        <Icon name="arrow-up-right" size={13} />
                        {link.is_mock && <span className="agent__msg-mock">mock</span>}
                      </a>
                    )}
                    {result?.link_note && <p className="agent__msg-note">{result.link_note}</p>}
                  </Card>
                )}

                <Card className="agent__trace">
                  <h3>Reasoning trace</h3>
                  <ol className="trace">
                    {result.trace?.map((t, i) => (
                      <li key={i} className="trace__line">
                        <span className="trace__n mono">{String(i + 1).padStart(2, "0")}</span>
                        <span className="trace__t">{t}</span>
                      </li>
                    ))}
                  </ol>
                </Card>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}
