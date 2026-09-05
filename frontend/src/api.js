// Base URL for the API. Empty by default so local dev (Vite proxy) and the
// single-origin Docker build "just work". For a split deploy (backend on its
// own host, e.g. Render), set VITE_API_BASE to that origin at build time.
export const API_BASE = import.meta.env.VITE_API_BASE ?? "";

async function j(url, opts) {
  const r = await fetch(API_BASE + url, opts);
  if (!r.ok) {
    let detail = "";
    try {
      const body = await r.json();
      if (Array.isArray(body?.detail)) {
        detail = body.detail.map((d) => `${d.loc?.slice(-1)}: ${d.msg}`).join("; ");
      } else if (body?.detail) {
        detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
      }
    } catch {
      /* non-JSON error body */
    }
    throw new Error(detail ? `${r.status} — ${detail}` : `${url} → ${r.status}`);
  }
  return r.json();
}

export const api = {
  health: () => j("/health"),
  metrics: () => j("/api/metrics"),
  cases: (params = {}) => {
    const q = new URLSearchParams(params).toString();
    return j(`/api/cases?${q}`);
  },
  reasons: () => j("/api/reasons"),
  riskOverview: () => j("/api/risk/overview"),
  riskPlan: (source, klass) =>
    j(`/api/risk/plan?source=${encodeURIComponent(source)}${klass ? `&klass=${encodeURIComponent(klass)}` : ""}`),
  plan: (body, signal) =>
    j("/api/plan", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal,
    }),
  advanceClock: () => j("/api/scheduler/advance", { method: "POST" }),
  checkRecovery: () => j("/api/recovery/check", { method: "POST" }),
  chaos: (llm, gateway) =>
    j(`/api/chaos?llm=${!!llm}&gateway=${!!gateway}`, { method: "POST" }),
};

export function formatINR(paise) {
  if (paise == null) return "—";
  const r = paise / 100;
  if (r >= 1e7) return `₹${(r / 1e7).toFixed(2)}Cr`;
  if (r >= 1e5) return `₹${(r / 1e5).toFixed(2)}L`;
  return `₹${Math.round(r).toLocaleString("en-IN")}`;
}

export const pct = (x) => `${(x * 100).toFixed(1)}%`;
