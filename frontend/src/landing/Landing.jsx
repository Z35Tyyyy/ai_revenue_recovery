import React from "react";
import { Nav } from "./Nav.jsx";
import { Hero } from "./Hero.jsx";
import { Problem } from "./Problem.jsx";
import { Intelligence } from "./Intelligence.jsx";
import { Agent } from "./Agent.jsx";
import { Learning } from "./Learning.jsx";
import { Impact } from "./Impact.jsx";
import { Gateway } from "./Gateway.jsx";
import { useMetrics } from "../lib/useData.js";

export default function Landing() {
  const { metrics } = useMetrics();
  return (
    <div className="lp">
      <Nav />
      <Hero />
      <Problem />
      <Intelligence />
      <Agent />
      <Learning bandit={metrics?.holdout?.bandit} />
      <Impact metrics={metrics} />
      <Gateway />
    </div>
  );
}
