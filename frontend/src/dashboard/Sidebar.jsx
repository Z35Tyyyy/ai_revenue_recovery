import React from "react";
import { Link, NavLink } from "react-router-dom";

const NAV = [
  { to: "/dashboard", label: "Overview", end: true },
  { to: "/dashboard/recoveries", label: "Recoveries" },
  { to: "/dashboard/agent", label: "Agent" },
  { to: "/dashboard/learning", label: "Learning" },
  { to: "/dashboard/experiments", label: "Experiments" },
  { to: "/dashboard/settings", label: "Settings" },
];

export function Sidebar() {
  return (
    <aside className="dash-side">
      <Link to="/" className="side-brand">
        <span className="glyph"><span /></span>
        Revenue Recovery
      </Link>
      <nav className="side-nav">
        {NAV.map((n) => (
          <NavLink
            key={n.to}
            to={n.to}
            end={n.end}
            className={({ isActive }) => `side-link ${isActive ? "active" : ""}`}
          >
            {n.label}
          </NavLink>
        ))}
      </nav>
      <div className="side-foot">
        <Link to="/">← Back to story</Link>
      </div>
    </aside>
  );
}
