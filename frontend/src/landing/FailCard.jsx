import React, { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Dot } from "../components/primitives.jsx";

const SCENARIOS = [
  { amount: "₹1,499", reason: "insufficient_funds", method: "UPI AutoPay", label: "Insufficient funds" },
  { amount: "₹12,499", reason: "needs_card_update", method: "Card", label: "Card expired" },
  { amount: "₹899", reason: "authentication_failed", method: "Card", label: "Authentication required" },
  { amount: "₹4,999", reason: "issuer_unavailable", method: "Netbanking", label: "Temporary bank failure" },
  { amount: "₹2,499", reason: "mandate_paused", method: "e-Mandate", label: "Payment method issue" },
];

export function FailCard({ interval = 2600 }) {
  const [i, setI] = useState(0);
  useEffect(() => {
    const t = setInterval(() => setI((x) => (x + 1) % SCENARIOS.length), interval);
    return () => clearInterval(t);
  }, [interval]);
  const s = SCENARIOS[i];

  return (
    <div className="fail-card">
      <div className="top">
        <div>
          <AnimatePresence mode="wait">
            <motion.div
              key={s.amount}
              className="amt tnum"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.35 }}
            >
              {s.amount}
            </motion.div>
          </AnimatePresence>
        </div>
        <span className="state"><Dot color="var(--red)" /> Payment failed</span>
      </div>
      <div className="rows">
        <div className="frow">
          <span className="lbl">reason</span>
          <AnimatePresence mode="wait">
            <motion.span
              key={s.reason}
              className="val"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.3 }}
            >
              {s.reason}
            </motion.span>
          </AnimatePresence>
        </div>
        <div className="frow">
          <span className="lbl">method</span>
          <span className="val">{s.method}</span>
        </div>
        <div className="frow">
          <span className="lbl">diagnosis</span>
          <AnimatePresence mode="wait">
            <motion.span
              key={s.label}
              className="val"
              style={{ color: "var(--text-dim)" }}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.3 }}
            >
              {s.label}
            </motion.span>
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}

export { SCENARIOS };
