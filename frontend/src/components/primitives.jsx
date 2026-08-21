import React from "react";

export function Button({ variant = "ghost", size, className = "", children, ...rest }) {
  const cls = ["btn", `btn-${variant}`, size === "lg" ? "btn-lg" : "", className]
    .filter(Boolean)
    .join(" ");
  return (
    <button className={cls} {...rest}>
      {children}
    </button>
  );
}

export function Card({ pad = true, hover = false, className = "", children, ...rest }) {
  const cls = ["card", pad ? "card-pad" : "", hover ? "card-hover" : "", className]
    .filter(Boolean)
    .join(" ");
  return (
    <div className={cls} {...rest}>
      {children}
    </div>
  );
}

export function Badge({ on = false, children }) {
  return (
    <span className={`badge ${on ? "on" : ""}`}>
      <span className="dot" />
      {children}
    </span>
  );
}

export function Chip({ variant = "", mono = false, children }) {
  return <span className={`chip ${variant} ${mono ? "mono" : ""}`}>{children}</span>;
}

export function Eyebrow({ children }) {
  return <div className="eyebrow">{children}</div>;
}

export function Dot({ color }) {
  return <span className="dot-lg" style={{ background: color }} />;
}

export function StatusPill({ status }) {
  const label = { recovered: "Recovered", halted: "Halted", gave_up: "Gave up",
    in_progress: "In progress", open: "Open" }[status] || status;
  return <span className={`status-pill status-${status}`}>{label}</span>;
}
