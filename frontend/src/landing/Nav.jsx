import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Button, Icon } from "../components/ui.jsx";

export function Logo({ size = 26 }) {
  return (
    <span className="logo" aria-hidden="true">
      <svg width={size} height={size} viewBox="0 0 32 32" fill="none">
        <circle cx="16" cy="16" r="15" stroke="var(--line-3)" />
        <path
          d="M11 13.5A6 6 0 0 1 22 15M21 18.5A6 6 0 0 1 10 17"
          stroke="var(--pos)"
          strokeWidth="1.7"
          strokeLinecap="round"
        />
        <path d="M22 11v4h-4M10 21v-4h4" stroke="var(--pos)" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </span>
  );
}

export function Nav() {
  const [scrolled, setScrolled] = useState(false);
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 24);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header className={`nav ${scrolled ? "nav--solid" : ""}`}>
      <div className="nav__inner container">
        <a href="#top" className="nav__brand">
          <Logo />
          <span className="nav__name">
            Revenue Recovery<span className="nav__sub">/ agentic engine</span>
          </span>
        </a>
        <nav className="nav__links" aria-label="Sections">
          <a href="#problem">The leak</a>
          <a href="#engine">The engine</a>
          <a href="#impact">The proof</a>
        </nav>
        <Button as={Link} to="/dashboard" variant="ghost" size="sm" className="nav__cta">
          Open console <Icon name="arrow" size={15} />
        </Button>
      </div>
    </header>
  );
}
