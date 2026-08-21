import React from "react";
import { motion } from "framer-motion";
import { fadeUp, stagger, viewport } from "../lib/motion.js";

/** Fade-and-rise a block into view once. */
export function Reveal({ as = "div", delay = 0, y = 22, className = "", children, ...rest }) {
  const M = motion[as] || motion.div;
  return (
    <M
      className={className}
      initial="hidden"
      whileInView="show"
      viewport={viewport}
      variants={{
        hidden: { opacity: 0, y },
        show: { opacity: 1, y: 0, transition: { duration: 0.6, ease: [0.22, 1, 0.36, 1], delay } },
      }}
      {...rest}
    >
      {children}
    </M>
  );
}

/** Stagger children (each child should be a <Stagger.Item>). */
export function Stagger({ gap = 0.09, delay = 0, className = "", children }) {
  return (
    <motion.div
      className={className}
      initial="hidden"
      whileInView="show"
      viewport={viewport}
      variants={stagger(gap, delay)}
    >
      {children}
    </motion.div>
  );
}

Stagger.Item = function Item({ className = "", children, ...rest }) {
  return (
    <motion.div className={className} variants={fadeUp} {...rest}>
      {children}
    </motion.div>
  );
};
