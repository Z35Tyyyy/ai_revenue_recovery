import React from "react";
import { motion } from "framer-motion";

/** A horizontal bar that grows to its value when scrolled into view. */
export function Bar({ value = 0, max = 1, tone = "blue", delay = 0 }) {
  const pct = Math.max(0, Math.min(1, value / max)) * 100;
  return (
    <div className="bar-track">
      <motion.div
        className={`bar-fill fill-${tone}`}
        initial={{ width: 0 }}
        whileInView={{ width: `${pct}%` }}
        viewport={{ once: true, margin: "-15% 0px" }}
        transition={{ duration: 0.9, ease: [0.22, 1, 0.36, 1], delay }}
      />
    </div>
  );
}
