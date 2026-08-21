import React from "react";
import { Route, Routes } from "react-router-dom";
import { Sidebar } from "./Sidebar.jsx";
import { Overview } from "./Overview.jsx";
import { Recoveries } from "./Recoveries.jsx";
import { AgentConsole } from "./AgentConsole.jsx";
import { LearningConsole } from "./LearningConsole.jsx";
import { Experiments } from "./Experiments.jsx";
import { Settings } from "./Settings.jsx";
import { Badge } from "../components/primitives.jsx";
import { useHealth } from "../lib/useData.js";

function Topbar() {
  const health = useHealth();
  return (
    <div className="dash-top">
      <span className="top-title">Console</span>
      <div className="top-caps">
        <Badge on={!!health?.razorpay_live}>
          {health?.razorpay_live ? "Razorpay live" : "Razorpay mock"}
        </Badge>
        <Badge on={!!health?.llm_enabled}>
          {health?.llm_enabled ? `Agent · ${health.llm_provider}` : "Agent · templates"}
        </Badge>
        {health?.sample_cases != null && <Badge on>{health.sample_cases} episodes</Badge>}
      </div>
    </div>
  );
}

export default function DashboardShell() {
  return (
    <div className="dash">
      <Sidebar />
      <div className="dash-main">
        <Topbar />
        <div className="dash-body">
          <Routes>
            <Route index element={<Overview />} />
            <Route path="recoveries" element={<Recoveries />} />
            <Route path="agent" element={<AgentConsole />} />
            <Route path="learning" element={<LearningConsole />} />
            <Route path="experiments" element={<Experiments />} />
            <Route path="settings" element={<Settings />} />
          </Routes>
        </div>
      </div>
    </div>
  );
}
