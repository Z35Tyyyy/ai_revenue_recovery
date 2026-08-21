import React, { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { api, pct } from "../api.js";
import { Card, Chip } from "../components/primitives.jsx";
import { Bar } from "../components/Bar.jsx";
import { actionLabel } from "../lib/labels.js";

const LANGS = ["hinglish", "hi", "en", "ta", "te", "mr", "kn", "bn"];
const CHANNELS = ["whatsapp", "email", "sms", "in_app"];
const METHODS = ["upi_autopay", "card", "emandate", "netbanking"];

export function AgentConsole() {
  const [reasons, setReasons] = useState([]);
  const [form, setForm] = useState({
    reason_code: "insufficient_funds", amount_paise: 49900, method: "upi_autopay",
    language: "hinglish", preferred_channel: "whatsapp", salary_day: 1, tenure_months: 18,
  });
  const [res, setRes] = useState(null);
  const [busy, setBusy] = useState(false);
  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  useEffect(() => { api.reasons().then((r) => setReasons(r.reasons)).catch(() => {}); }, []);

  async function run() {
    setBusy(true);
    try { setRes(await api.plan({ ...form, amount_paise: Number(form.amount_paise) })); }
    catch { setRes({ error: true }); }
    finally { setBusy(false); }
  }

  const alts = res && !res.error
    ? res.candidates.filter((c) => c.action !== res.decision.action && c.action !== "give_up").slice(0, 4)
    : [];
  const maxAlt = Math.max(0.01, ...alts.map((a) => a.prob), res?.decision?.prob || 0);

  return (
    <div>
      <div className="page-h">
        <h1>Agent</h1>
        <p>Hand the agent a failed charge and watch it decide, in real time.</p>
      </div>

      <div className="agent-cols">
        <Card>
          <div className="form-grid">
            <div className="field">
              <label>Failure reason</label>
              <select value={form.reason_code} onChange={(e) => set("reason_code", e.target.value)}>
                {reasons.map((r) => <option key={r.code} value={r.code}>{r.code}</option>)}
              </select>
            </div>
            <div className="field">
              <label>Amount (₹)</label>
              <input type="number" value={form.amount_paise / 100}
                onChange={(e) => set("amount_paise", Math.round(Number(e.target.value) * 100))} />
            </div>
            <div className="field">
              <label>Payment method</label>
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
          <button className="btn btn-primary" style={{ marginTop: 16, width: "100%" }} onClick={run} disabled={busy}>
            {busy ? "Thinking…" : "Diagnose & recover →"}
          </button>
        </Card>

        <div>
          <AnimatePresence mode="wait">
            {!res && (
              <motion.div key="empty" className="agent-empty" exit={{ opacity: 0 }}>
                Configure a failed charge and run the agent to see its decision.
              </motion.div>
            )}
            {res?.error && (
              <motion.div key="err" className="agent-empty">
                Start the API (<span className="mono">make api</span>) to run the agent.
              </motion.div>
            )}
            {res && !res.error && (
              <motion.div key="res" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
                <div className="decision-card">
                  <div className="dk">Recommended action</div>
                  <div className="dv">{actionLabel(res.decision.action)}</div>
                  <div className="dconf" style={{ marginTop: 8 }}>
                    <Chip variant="good">{pct(res.decision.prob)} confidence</Chip>
                    <span className="chip mono" style={{ marginLeft: 8 }}>{res.decision.action}</span>
                  </div>
                </div>

                {alts.length > 0 && (
                  <Card style={{ marginTop: 16 }}>
                    <div className="d-k" style={{ marginBottom: 12 }}>Alternatives considered</div>
                    <div className="alt-list">
                      {alts.map((a) => (
                        <div className="alt-row" key={a.action}>
                          <span className="aln">{actionLabel(a.action)}</span>
                          <div className="alt"><Bar value={a.prob} max={maxAlt} tone="blue" /></div>
                          <span className="alv">{pct(a.prob)}</span>
                        </div>
                      ))}
                    </div>
                  </Card>
                )}

                <Card style={{ marginTop: 16 }}>
                  <div className="d-k" style={{ marginBottom: 12 }}>Reasoning trace</div>
                  <div className="trace-list">
                    {res.trace.map((t, i) => (
                      <div className="trace-item" key={i}>
                        <span className="ti">{String(i + 1).padStart(2, "0")}</span><span>{t}</span>
                      </div>
                    ))}
                  </div>
                </Card>

                {res.message && (
                  <Card style={{ marginTop: 16 }}>
                    <div className="d-k" style={{ marginBottom: 10 }}>Generated message</div>
                    <div className="msg-box">
                      <div className="msg-meta">
                        {res.message.language} · via {res.message.channel} · authored by {res.message.authored_by}
                      </div>
                      {res.message.text}
                    </div>
                    {res.payment_link && (
                      <div style={{ marginTop: 12 }}>
                        <div className="msg-meta">
                          {res.payment_link.is_mock ? "Mock payment link" : "Live Razorpay test-mode link"} · {res.payment_link.amount}
                        </div>
                        <div className="link-box">{res.payment_link.short_url}</div>
                      </div>
                    )}
                  </Card>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}
