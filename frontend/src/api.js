async function j(url, opts) {
  const r = await fetch(url, opts);
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
  plan: (body, signal) =>
    j("/api/plan", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal,
    }),
  advanceClock: () => j("/api/scheduler/advance", { method: "POST" }),
};

export function formatINR(paise) {
  if (paise == null) return "—";
  const r = paise / 100;
  if (r >= 1e7) return `₹${(r / 1e7).toFixed(2)}Cr`;
  if (r >= 1e5) return `₹${(r / 1e5).toFixed(2)}L`;
  return `₹${Math.round(r).toLocaleString("en-IN")}`;
}

export const pct = (x) => `${(x * 100).toFixed(1)}%`;
