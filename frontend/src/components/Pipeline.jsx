import React from "react";
import { motion } from "framer-motion";
import { viewport } from "../lib/motion.js";

/**
 * The signature flow visual: a sequence of stages joined by connectors, with a
 * pulse that travels through as it enters view. Vertical by default; horizontal
 * on wide screens when `orientation="horizontal"`.
 */
export function Pipeline({ stages, orientation = "vertical", accentIndex = -1, className = "" }) {
  const n = stages.length;
  return (
    <motion.div
      className={`pipe pipe-${orientation} ${className}`}
      initial="hidden"
      whileInView="show"
      viewport={viewport}
      variants={{ hidden: {}, show: { transition: { staggerChildren: 0.14 } } }}
    >
      {stages.map((s, i) => {
        const accent = i === accentIndex;
        return (
          <React.Fragment key={i}>
            <motion.div
              className={`pipe-node ${accent ? "accent" : ""}`}
              variants={{
                hidden: { opacity: 0, y: orientation === "vertical" ? 14 : 0, scale: 0.97 },
                show: { opacity: 1, y: 0, scale: 1, transition: { duration: 0.5, ease: [0.22, 1, 0.36, 1] } },
              }}
            >
              <span className="pipe-idx mono">{String(i + 1).padStart(2, "0")}</span>
              <span className="pipe-label">{s.label}</span>
              {s.sub && <span className="pipe-sub">{s.sub}</span>}
            </motion.div>
            {i < n - 1 && (
              <motion.div
                className="pipe-conn"
                variants={{
                  hidden: { opacity: 0 },
                  show: { opacity: 1, transition: { duration: 0.3 } },
                }}
              >
                <span className="pipe-line" />
                <motion.span
                  className="pipe-pulse"
                  initial={{ opacity: 0 }}
                  animate={
                    orientation === "vertical"
                      ? { top: ["0%", "100%"], opacity: [0, 1, 1, 0] }
                      : { left: ["0%", "100%"], opacity: [0, 1, 1, 0] }
                  }
                  transition={{ duration: 1.6, repeat: Infinity, repeatDelay: 1.1, ease: "easeInOut", delay: i * 0.2 }}
                />
              </motion.div>
            )}
          </React.Fragment>
        );
      })}
    </motion.div>
  );
}
