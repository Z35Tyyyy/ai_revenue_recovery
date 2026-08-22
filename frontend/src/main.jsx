import React, { Suspense, lazy } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, HashRouter, Route, Routes } from "react-router-dom";

import "./theme/tokens.css";
import "./theme/base.css";
import "./theme/components.css";
import "./theme/landing.css";
import "./theme/dashboard.css";

import { ErrorBoundary } from "./components/ui.jsx";
import Landing from "./landing/Landing.jsx";

const DashboardShell = lazy(() => import("./dashboard/DashboardShell.jsx"));

function Fallback() {
  return <div className="route-fallback">Loading…</div>;
}

// Hash routing for the standalone single-file preview (no server); browser
// routing for the normal app served by FastAPI/Vite.
const Router = import.meta.env.VITE_HASH ? HashRouter : BrowserRouter;

createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <Router>
      <ErrorBoundary>
        <Suspense fallback={<Fallback />}>
          <Routes>
            <Route path="/" element={<Landing />} />
            <Route path="/dashboard/*" element={<DashboardShell />} />
          </Routes>
        </Suspense>
      </ErrorBoundary>
    </Router>
  </React.StrictMode>
);
