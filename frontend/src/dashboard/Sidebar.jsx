import React from "react";
import { Link, NavLink } from "react-router-dom";
import { Logo } from "../landing/Nav.jsx";

const I = (d) => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
    {d}
  </svg>
);

const NAV = [
  { to: "/dashboard", label: "Console", end: true, icon: I(<><rect x="3" y="3" width="8" height="8" rx="1.5" /><rect x="13" y="3" width="8" height="5" rx="1.5" /><rect x="13" y="11" width="8" height="10" rx="1.5" /><rect x="3" y="14" width="8" height="7" rx="1.5" /></>) },
  { to: "/dashboard/live", label: "Live", icon: I(<><circle cx="12" cy="12" r="9" /><path d="M10 8.5l6 3.5-6 3.5v-7Z" fill="currentColor" stroke="none" /></>) },
  { to: "/dashboard/recoveries", label: "Recoveries", icon: I(<><path d="M4 6h16M4 12h16M4 18h16" /><circle cx="4" cy="6" r="0.6" fill="currentColor" /></>) },
  { to: "/dashboard/exceptions", label: "Exceptions", icon: I(<><path d="M12 3l9 16H3L12 3Z" /><path d="M12 10v4M12 17h.01" /></>) },
  { to: "/dashboard/agent", label: "Agent", icon: I(<><rect x="4" y="6" width="16" height="12" rx="2" /><path d="M9 11h.01M15 11h.01M9 15h6M12 3v3" /></>) },
  { to: "/dashboard/experiments", label: "Experiments", icon: I(<><path d="M9 3v6l-5 8a2 2 0 0 0 2 3h12a2 2 0 0 0 2-3l-5-8V3M8 3h8M8 14h8" /></>) },
];

export function Sidebar({ online }) {
  return (
    <aside className="side">
      <Link to="/" className="side__brand">
        <Logo size={24} />
        <span>
          Re<span className="side__brand-dim">bound</span>
        </span>
      </Link>

      <nav className="side__nav" aria-label="Console sections">
        {NAV.map((n) => (
          <NavLink
            key={n.to}
            to={n.to}
            end={n.end}
            className={({ isActive }) => `side__link ${isActive ? "is-active" : ""}`}
          >
            <span className="side__icon">{n.icon}</span>
            {n.label}
          </NavLink>
        ))}
      </nav>

      <div className="side__foot">
        <div className="side__status">
          <span className={`side__pulse ${online ? "is-on" : "is-off"}`} />
          {online ? "Engine online" : "Offline · sample data"}
        </div>
        <Link to="/" className="side__back">
          ← Back to story
        </Link>
      </div>
    </aside>
  );
}
