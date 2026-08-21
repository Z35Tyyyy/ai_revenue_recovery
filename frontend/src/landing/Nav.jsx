import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";

export function Nav() {
  const [scrolled, setScrolled] = useState(false);
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 24);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <nav className={`lp-nav ${scrolled ? "scrolled" : ""}`}>
      <div className="lp-nav-inner container">
        <div className="brandmark">
          <span className="glyph"><span /></span>
          AI Revenue Recovery
        </div>
        <Link to="/dashboard" className="btn btn-ghost">
          View live dashboard →
        </Link>
      </div>
    </nav>
  );
}
