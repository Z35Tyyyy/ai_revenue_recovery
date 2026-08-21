import React from "react";
import { Route, Routes } from "react-router-dom";
import { Sidebar } from "./Sidebar.jsx";
import { Overview } from "./Overview.jsx";
import { Recoveries } from "./Recoveries.jsx";
import { ComingSoon } from "./ComingSoon.jsx";
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
            <Route
              path="agent"
              element={<ComingSoon title="Agent" desc="Interactive diagnose-and-recover console — submit a failed charge and watch the agent decide, with a live message and payment link." />}
            />
            <Route
              path="learning"
              element={<ComingSoon title="Learning" desc="Inspect what the contextual bandit learned per failure class, and how its preferred intervention emerged from outcomes." />}
            />
            <Route
              path="experiments"
              element={<ComingSoon title="Experiments" desc="Compare recovery policies head-to-head on identical ground truth — recovery rate, revenue, retries, and time-to-recover." />}
            />
            <Route
              path="settings"
              element={<ComingSoon title="Settings" desc="Engine capabilities and configuration — Razorpay mode, dunning provider, seed, and model details." />}
            />
          </Routes>
        </div>
      </div>
    </div>
  );
}
