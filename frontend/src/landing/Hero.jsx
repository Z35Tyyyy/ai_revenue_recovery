import React, { useRef } from "react";
import { motion, useScroll, useTransform } from "framer-motion";
import { Link } from "react-router-dom";
import { Pipeline } from "../components/Pipeline.jsx";
import { Eyebrow } from "../components/primitives.jsx";

const STAGES = [
  { label: "Payment", sub: "recurring charge attempted" },
  { label: "Failure", sub: "the debit bounces" },
  { label: "Agent", sub: "understands why" },
  { label: "Decision", sub: "chooses the intervention" },
  { label: "Recovery", sub: "revenue reclaimed" },
];

export function Hero() {
  const ref = useRef(null);
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start start", "end start"] });
  const y = useTransform(scrollYProgress, [0, 1], [0, -70]);
  const opacity = useTransform(scrollYProgress, [0, 0.75], [1, 0]);

  const toProblem = () =>
    document.getElementById("problem")?.scrollIntoView({ behavior: "smooth" });

  return (
    <section className="hero" ref={ref}>
      <div className="hero-atmos" />
      <div className="hero-grid" />
      <motion.div className="hero-inner container" style={{ y, opacity }}>
        <div className="hero-copy">
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }}>
            <Eyebrow>AI Revenue Recovery · for Razorpay</Eyebrow>
          </motion.div>
          <motion.h1
            className="display"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.08 }}
          >
            Failed payments<br />shouldn't be the end.
          </motion.h1>
          <motion.p
            className="lead"
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.18 }}
          >
            An agentic recovery engine that understands <em style={{ color: "var(--text)", fontStyle: "normal" }}>why</em> payments
            fail, chooses the right intervention, and learns what actually works.
          </motion.p>
          <motion.div
            className="hero-cta"
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.28 }}
          >
            <button className="btn btn-primary btn-lg" onClick={toProblem}>Explore the engine ↓</button>
            <Link to="/dashboard" className="btn btn-subtle btn-lg">View live dashboard →</Link>
          </motion.div>
        </div>
        <div className="hero-viz">
          <Pipeline stages={STAGES} orientation="vertical" accentIndex={4} />
        </div>
      </motion.div>
      <motion.div
        className="scroll-hint"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1, duration: 1 }}
      >
        <span>Scroll</span>
        <motion.span animate={{ y: [0, 6, 0] }} transition={{ duration: 1.6, repeat: Infinity }}>↓</motion.span>
      </motion.div>
    </section>
  );
}
