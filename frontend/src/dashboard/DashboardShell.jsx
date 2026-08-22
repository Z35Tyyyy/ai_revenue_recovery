import React from "react";
import { Route, Routes, useLocation } from "react-router-dom";
import { Sidebar } from "./Sidebar.jsx";
import { Overview } from "./Overview.jsx";
import { Live } from "./Live.jsx";
import { Recoveries } from "./Recoveries.jsx";
import { AgentConsole } from "./AgentConsole.jsx";
import { LearningConsole } from "./LearningConsole.jsx";
import { Experiments } from "./Experiments.jsx";
import { Settings } from "./Settings.jsx";
import { ErrorBoundary, Pill } from "../components/ui.jsx";
import { useHealth } from "../lib/useData.js";

const TITLES = {
  "/dashboard": "Overview",
  "/dashboard/live": "Live",
  "/dashboard/recoveries": "Recoveries",
  "/dashboard/agent": "Agent",
  "/dashboard/learning": "Learning",
  "/dashboard/experiments": "Experiments",
  "/dashboard/settings": "Settings",
};

function Topbar({ health, online }) {
  const loc = useLocation();
  const title = TITLES[loc.pathname.replace(/\/$/, "")] || "Console";
  return (
    <header className="top">
      <div className="top__title">
        <span className="top__crumb mono">console</span>
        <h1>{title}</h1>
      </div>
      <div className="top__caps">
        {!online && <Pill tone="warn">offline · sample data</Pill>}
        <Pill tone={health?.razorpay_live ? "pos" : "neutral"} icon>
          {health?.razorpay_live ? "Razorpay live" : "Razorpay mock"}
        </Pill>
        <Pill tone={health?.llm_enabled ? "cool" : "neutral"} icon>
          {health?.llm_enabled ? `Agent · ${health.llm_provider}` : "Agent · templates"}
        </Pill>
      </div>
    </header>
  );
}

export default function DashboardShell() {
  const { health, online } = useHealth();
  return (
    <div className="dash">
      <Sidebar online={online} />
      <div className="dash__main">
        <Topbar health={health} online={online} />
        <div className="dash__body">
          <ErrorBoundary>
            <Routes>
              <Route index element={<Overview />} />
              <Route path="live" element={<Live />} />
              <Route path="recoveries" element={<Recoveries />} />
              <Route path="agent" element={<AgentConsole />} />
              <Route path="learning" element={<LearningConsole />} />
              <Route path="experiments" element={<Experiments />} />
              <Route path="settings" element={<Settings />} />
            </Routes>
          </ErrorBoundary>
        </div>
      </div>
    </div>
  );
}
