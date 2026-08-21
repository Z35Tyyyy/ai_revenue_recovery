# Dashboard (React + Vite)

The analytics UI for the AI Revenue Recovery engine.

## Run

```bash
# 1) start the backend (from the repo root)
make api            # FastAPI on :8000

# 2) start the dashboard (this directory)
npm install
npm run dev         # Vite on :5173  →  open http://localhost:5173
```

The dev server proxies `/api`, `/health`, and `/webhooks` to the backend on
`:8000` (see `vite.config.js`), so no CORS or extra config is needed.

## What it shows

- **Held-out KPIs** — recovery rate, uplift vs the fixed-retry default, revenue
  recovered, and triage AUC (from `reports/eval.json`).
- **Policy comparison** — recovery rate for every policy on identical ground truth.
- **Recovery by failure class** — where the engine beats a blind retry.
- **Try the agent** — POST a synthetic failed charge to `/api/plan` and watch it
  diagnose, decide, generate a localised message, and mint a payment link.
- **What the bandit learned** — the converged best action per failure class.
- **Live recovery stream** — executed episodes; click one for the reasoning trace.

## Build

```bash
npm run build       # → dist/  (static, self-contained)
```
