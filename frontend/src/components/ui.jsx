import React, { useEffect, useRef, useState } from "react";
import { animate, motion, useInView, useReducedMotion } from "framer-motion";

/* ------------------------------------------------------------------ motion */

export const EASE = [0.22, 1, 0.36, 1];

export const fadeUp = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0, transition: { duration: 0.6, ease: EASE } },
};
export const fadeIn = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { duration: 0.7, ease: EASE } },
};
export const stagger = (gap = 0.07, delay = 0) => ({
  hidden: {},
  show: { transition: { staggerChildren: gap, delayChildren: delay } },
});

/** Scroll-reveal wrapper. Collapses to a static div when reduce-motion is set. */
export function Reveal({ children, as = "div", variants = fadeUp, className, style, once = true }) {
  const reduce = useReducedMotion();
  const ref = useRef(null);
  const inView = useInView(ref, { once, margin: "-12% 0px -12% 0px" });
  const M = motion[as] || motion.div;
  if (reduce) {
    const Tag = as;
    return (
      <Tag ref={ref} className={className} style={style}>
        {children}
      </Tag>
    );
  }
  return (
    <M
      ref={ref}
      className={className}
      style={style}
      variants={variants}
      initial="hidden"
      animate={inView ? "show" : "hidden"}
    >
      {children}
    </M>
  );
}

/** Count-up number. Animates on mount and always settles on the exact value;
    jumps straight to the final value under reduce-motion. */
export function Counter({ to, format = (n) => Math.round(n).toLocaleString("en-IN"), duration = 1.3, className }) {
  const reduce = useReducedMotion();
  const [text, setText] = useState(() => format(reduce ? to : 0));

  useEffect(() => {
    if (reduce || !Number.isFinite(to)) {
      setText(format(to));
      return;
    }
    const controls = animate(0, to, {
      duration,
      ease: EASE,
      onUpdate: (v) => setText(format(v)),
      onComplete: () => setText(format(to)),
    });
    // Backstop: guarantee the exact final value even if the rAF loop never ticks.
    const settle = setTimeout(() => setText(format(to)), duration * 1000 + 350);
    return () => {
      controls.stop();
      clearTimeout(settle);
    };
  }, [to, reduce, duration]); // eslint-disable-line react-hooks/exhaustive-deps

  return <span className={`tnum ${className || ""}`}>{text}</span>;
}

/* ----------------------------------------------------------------- surfaces */

export function Card({ children, className = "", hover = false, glow = false, as = "div", ...rest }) {
  const Tag = as;
  return (
    <Tag
      className={`card ${hover ? "card--hover" : ""} ${glow ? "card--glow" : ""} ${className}`}
      {...rest}
    >
      {children}
    </Tag>
  );
}

export function Divider({ vertical = false, className = "" }) {
  return <span className={`divider ${vertical ? "divider--v" : ""} ${className}`} aria-hidden="true" />;
}

/* -------------------------------------------------------------------- chips */

export function Pill({ children, tone = "neutral", soft = true, className = "", icon }) {
  return (
    <span className={`pill pill--${tone} ${soft ? "pill--soft" : "pill--solid"} ${className}`}>
      {icon && <span className="pill__dot" style={{ background: "currentColor" }} />}
      {children}
    </span>
  );
}

/* ------------------------------------------------------------------ buttons */

export function Button({ children, variant = "primary", size = "md", as = "button", className = "", ...rest }) {
  const Tag = as;
  return (
    <Tag className={`btn btn--${variant} btn--${size} ${className}`} {...rest}>
      {children}
    </Tag>
  );
}

/* --------------------------------------------------------------------- stat */

export function Stat({ label, value, unit, delta, deltaTone = "pos", sub, mono = false, big = false }) {
  return (
    <div className={`stat ${big ? "stat--big" : ""}`}>
      <div className="stat__label">{label}</div>
      <div className={`stat__value ${mono ? "mono" : "tnum"}`}>
        {value}
        {unit && <span className="stat__unit">{unit}</span>}
      </div>
      {(delta || sub) && (
        <div className="stat__foot">
          {delta && <span className={`stat__delta stat__delta--${deltaTone}`}>{delta}</span>}
          {sub && <span className="stat__sub">{sub}</span>}
        </div>
      )}
    </div>
  );
}

/* --------------------------------------------------------------------- meter */

/** Horizontal comparison bar. `value` 0..1. */
export function Meter({ value, tone = "pos", track = true, animated = true, height = 8 }) {
  const reduce = useReducedMotion();
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: "-8% 0px" });
  const pct = Math.max(0, Math.min(1, value || 0)) * 100;
  const shouldAnimate = animated && !reduce;
  return (
    <div ref={ref} className={`meter ${track ? "" : "meter--no-track"}`} style={{ height }} aria-hidden="true">
      <motion.span
        className={`meter__fill meter__fill--${tone}`}
        initial={shouldAnimate ? { width: 0 } : false}
        animate={{ width: `${inView || !shouldAnimate ? pct : 0}%` }}
        transition={{ duration: 0.9, ease: EASE }}
      />
    </div>
  );
}

/* ------------------------------------------------------------- error boundary */

export class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }
  static getDerivedStateFromError(error) {
    return { error };
  }
  componentDidCatch(error, info) {
    // eslint-disable-next-line no-console
    console.error("UI error boundary caught:", error, info);
  }
  render() {
    if (this.state.error) {
      return (
        this.props.fallback || (
          <div className="errbox">
            <div className="errbox__inner">
              <span className="eyebrow neg">Something broke</span>
              <h2>This view hit an error.</h2>
              <p>The rest of the app is fine — reload this panel to try again.</p>
              <Button variant="ghost" onClick={() => this.setState({ error: null })}>
                Retry
              </Button>
            </div>
          </div>
        )
      );
    }
    return this.props.children;
  }
}

/* --------------------------------------------------------------------- icons */

export function Icon({ name, size = 16, className = "" }) {
  const p = { width: size, height: size, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 1.6, strokeLinecap: "round", strokeLinejoin: "round", className };
  switch (name) {
    case "arrow":
      return (<svg {...p}><path d="M5 12h14M13 6l6 6-6 6" /></svg>);
    case "arrow-up-right":
      return (<svg {...p}><path d="M7 17 17 7M8 7h9v9" /></svg>);
    case "check":
      return (<svg {...p}><path d="M20 6 9 17l-5-5" /></svg>);
    case "spark":
      return (<svg {...p}><path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5 18 18M18 6l-2.5 2.5M8.5 15.5 6 18" /></svg>);
    case "bolt":
      return (<svg {...p} fill="currentColor" stroke="none"><path d="M13 2 4 14h6l-1 8 9-12h-6l1-8z" /></svg>);
    case "clock":
      return (<svg {...p}><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></svg>);
    case "message":
      return (<svg {...p}><path d="M21 15a2 2 0 0 1-2 2H8l-4 4V5a2 2 0 0 1 2-2h13a2 2 0 0 1 2 2z" /></svg>);
    case "link":
      return (<svg {...p}><path d="M10 13a5 5 0 0 0 7 0l2-2a5 5 0 0 0-7-7l-1 1M14 11a5 5 0 0 0-7 0l-2 2a5 5 0 0 0 7 7l1-1" /></svg>);
    case "close":
      return (<svg {...p}><path d="M18 6 6 18M6 6l12 12" /></svg>);
    case "dot":
      return (<svg width={size} height={size} viewBox="0 0 8 8" className={className}><circle cx="4" cy="4" r="4" fill="currentColor" /></svg>);
    default:
      return null;
  }
}

/* ------------------------------------------------------------------- helpers */

export const CLASS_TONE = {
  transient: "cool",
  insufficient_funds: "warn",
  soft_decline: "warn",
  needs_card_update: "cool",
  needs_reauth: "cool",
  hard_decline: "neg",
  unknown: "neutral",
};

export const STATUS_TONE = {
  recovered: "pos",
  open: "warn",
  halted: "warn",
  scheduled: "cool",
  gave_up: "neg",
};

export const ACTION_TONE = {
  retry_now: "cool",
  retry_optimal: "pos",
  dunning_nudge: "warn",
  request_card_update: "cool",
  switch_method: "warn",
  offer_grace: "warn",
  give_up: "neg",
  wait: "neutral",
};
