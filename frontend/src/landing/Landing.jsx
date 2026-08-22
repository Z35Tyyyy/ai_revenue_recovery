import React from "react";
import { Nav } from "./Nav.jsx";
import { Hero } from "./Hero.jsx";
import { Problem, Taxonomy, Loop } from "./Story.jsx";
import { Intelligence, Act, Learning } from "./Engine.jsx";
import { Impact, Gateway } from "./Impact.jsx";
import { useMetrics } from "../lib/useData.js";

export default function Landing() {
  const { metrics } = useMetrics();
  return (
    <div className="lp">
      <Nav />
      <main>
        <Hero metrics={metrics} />
        <Problem />
        <Taxonomy />
        <Loop />
        <Intelligence metrics={metrics} />
        <Act />
        <Learning bandit={metrics?.holdout?.bandit} />
        <Impact metrics={metrics} />
        <Gateway />
      </main>
    </div>
  );
}
