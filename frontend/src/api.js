async function j(url, opts) {
  const r = await fetch(url, opts);
  if (!r.ok) throw new Error(`${url} → ${r.status}`);
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
  plan: (body) =>
    j("/api/plan", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
};

export function formatINR(paise) {
  if (paise == null) return "—";
  const r = paise / 100;
  if (r >= 1e7) return `₹${(r / 1e7).toFixed(2)}Cr`;
  if (r >= 1e5) return `₹${(r / 1e5).toFixed(2)}L`;
  return `₹${Math.round(r).toLocaleString("en-IN")}`;
}

export const pct = (x) => `${(x * 100).toFixed(1)}%`;
