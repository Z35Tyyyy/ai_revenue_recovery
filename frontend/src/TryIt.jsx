import React, { useState } from "react";
import { api, formatINR, pct } from "./api.js";
import { Card } from "./ui.jsx";

const LANGS = ["hinglish", "hi", "en", "ta", "te", "mr", "kn", "bn"];
const CHANNELS = ["whatsapp", "email", "sms", "in_app"];
const METHODS = ["card", "upi_autopay", "emandate", "netbanking"];

export default function TryIt({ reasons }) {
  const [form, setForm] = useState({
    reason_code: "insufficient_funds",
    amount_paise: 49900,
    method: "upi_autopay",
    language: "hinglish",
    preferred_channel: "whatsapp",
    tenure_months: 18,
    salary_day: 1,
  });
  const [res, setRes] = useState(null);
  const [busy, setBusy] = useState(false);

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  async function run() {
    setBusy(true);
    try {
      setRes(await api.plan({ ...form, amount_paise: Number(form.amount_paise) }));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card>
      <div className="form">
        <div className="field">
          <label>Failure reason</label>
          <select value={form.reason_code} onChange={(e) => set("reason_code", e.target.value)}>
            {reasons.map((r) => (
              <option key={r.code} value={r.code}>{r.code}</option>
            ))}
          </select>
        </div>
        <div className="field">
          <label>Amount (₹)</label>
          <input
            type="number"
            value={form.amount_paise / 100}
            onChange={(e) => set("amount_paise", Math.round(Number(e.target.value) * 100))}
          />
        </div>
        <div className="field">
          <label>Method</label>
          <select value={form.method} onChange={(e) => set("method", e.target.value)}>
            {METHODS.map((m) => <option key={m}>{m}</option>)}
          </select>
        </div>
        <div className="field">
          <label>Language</label>
          <select value={form.language} onChange={(e) => set("language", e.target.value)}>
            {LANGS.map((l) => <option key={l}>{l}</option>)}
          </select>
        </div>
        <div className="field">
          <label>Preferred channel</label>
          <select value={form.preferred_channel} onChange={(e) => set("preferred_channel", e.target.value)}>
            {CHANNELS.map((c) => <option key={c}>{c}</option>)}
          </select>
        </div>
        <div className="field">
          <label>Salary day</label>
          <input type="number" min="1" max="31" value={form.salary_day}
            onChange={(e) => set("salary_day", Number(e.target.value))} />
        </div>
      </div>
      <button className="btn" onClick={run} disabled={busy}>
        {busy ? "Thinking…" : "Diagnose & recover →"}
      </button>

      {res && (
        <div style={{ marginTop: 16 }}>
          <div className="bars">
            {res.candidates.map((c) => (
              <div className="bar-row" key={c.action}>
                <div className={`name ${c.action === res.decision.action ? "eng" : ""}`}>{c.action}</div>
                <div className="track">
                  <div className={`fill ${c.action === res.decision.action ? "eng" : ""}`}
                    style={{ width: `${Math.min(100, c.prob * 100)}%` }} />
                </div>
                <div className="val">{pct(c.prob)}</div>
              </div>
            ))}
          </div>
          <div className="trace">
            <ul>{res.trace.map((t, i) => <li key={i}>{t}</li>)}</ul>
          </div>
          {res.message && (
            <div className="msg">
              <div className="lbl">
                Dunning · {res.message.language} · via {res.message.channel} · authored by {res.message.authored_by}
              </div>
              {res.message.text}
            </div>
          )}
          {res.payment_link && (
            <div className="msg">
              <div className="lbl">
                {res.payment_link.is_mock ? "Mock payment link (no Razorpay keys)" : "LIVE Razorpay test-mode link"}
                {" · "}{res.payment_link.amount}
              </div>
              <span className="link">{res.payment_link.short_url}</span>
            </div>
          )}
        </div>
      )}
    </Card>
  );
}
