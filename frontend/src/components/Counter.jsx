import React, { useEffect, useRef, useState } from "react";
import { animate, useInView } from "framer-motion";

/** Counts from 0 → value once it scrolls into view. */
export function Counter({ value = 0, duration = 1.4, format = (n) => n.toFixed(0), className = "" }) {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: "-20% 0px" });
  const [display, setDisplay] = useState(0);

  useEffect(() => {
    if (!inView) return;
    const controls = animate(0, value, {
      duration,
      ease: [0.22, 1, 0.36, 1],
      onUpdate: (v) => setDisplay(v),
    });
    return () => controls.stop();
  }, [inView, value, duration]);

  return (
    <span ref={ref} className={`tnum ${className}`}>
      {format(display)}
    </span>
  );
}
