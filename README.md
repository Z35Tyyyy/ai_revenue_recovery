<div align="center">

# ♻️ AI Revenue Recovery

### An agentic engine that recovers failed recurring payments on Razorpay

**Razorpay AI Buildathon 2026 — Track 3: AI Revenue Recovery**

*Diagnose → Predict → Decide → Act → Measure — a closed loop that turns involuntary churn back into revenue.*

</div>

---

## The experience

The product ships as two deliberately distinct surfaces. A **cinematic, scroll-driven story** explains the problem and the intelligence — then a calm, data-driven **operating console** where you actually run recoveries.

![Landing](docs/landing.png)

Story mode (`/`) → **Enter the console →** → operating mode (`/dashboard`): Overview, **Live**, Recoveries, Agent, Learning, Experiments, Settings.

![Console — Overview](docs/dashboard.png)

The **Live** page is where it stops being a report and starts being a *system*: a fresh stream of failed charges runs through the real engine in real time — a bandit learning as it goes — **racing the Razorpay fixed-retry default** on the same hidden ground truth. Reshape the failure world (an *expired-card wave*, a *payday crunch*, a *fraud spike*) and watch the policy react and the numbers recompute live. On the expired-card wave the engine recovers ~65% vs the default's ~37%, using a third of the retries — computed in front of you, not read from a file.

Every recovery opens a drawer with the agent's full reasoning trace — a decision log, not a debug dump.

![Console — Recoveries](docs/recoveries.png)

The **Agent** page hands the engine a failed charge live — recommended action, confidence, alternatives, the reasoning trace, and a generated multilingual message with a payment link:

![Console — Agent](docs/agent.png)

**Experiments** compares every policy on identical ground truth; **Learning** shows what the bandit converged to per failure class.

![Console — Experiments](docs/experiments.png)

---

## The problem

Subscription and recurring businesses lose **20–40% of recurring revenue to *involuntary* churn** — payments that fail for *recoverable* reasons: insufficient funds on debit day, an expired card, a bank in downtime, a soft "do-not-honour" decline, a UPI-autopay mandate hiccup. The customer never *chose* to leave; the payment just didn't go through.

Today the default response is blunt:

- **Fixed-schedule retries.** Razorpay auto-retries the next day. One dumb retry, same time, for every failure — whether the card is expired (retrying is pointless) or the customer is simply mid-month broke (retry on salary day and it sails through).
- **Generic dunning.** A single templated "your payment failed" email in English, to everyone, regardless of *why* it failed or *who* the customer is.

The state of the art (Stripe Smart Retries, Butter, FlyCode) uses ML to pick the optimal retry moment per card and orchestrate smarter dunning — and recovers meaningfully more. **There is no open, transparent, India-native version of this.** That's what this project is.

## The idea in one loop

For **every** failed recurring charge, an agent runs a closed decision loop:

```
  payment.failed ─▶  ┌───────────┐   ┌──────────┐   ┌──────────┐   ┌────────┐   ┌──────────┐
  (Razorpay          │ DIAGNOSE  │─▶ │ PREDICT  │─▶ │  DECIDE  │─▶ │  ACT   │─▶ │ MEASURE  │
   webhook)          │ taxonomy  │   │  ML: P(  │   │ agentic  │   │ retry /│   │ outcome  │
                     │ of failure│   │ recover),│   │ policy   │   │ dunning│   │ feeds    │
                     │ reason    │   │ best slot│   │ (bandit) │   │ + link │   │ back ↺   │
                     └───────────┘   └──────────┘   └──────────┘   └────────┘   └──────────┘
```

1. **Diagnose** — consume `payment.failed` / `subscription.halted` webhooks and map raw Razorpay error reason codes into a *recoverability taxonomy* (soft-retry vs. needs-card-update vs. needs-reauth vs. hard-decline vs. transient).
2. **Predict** — an ML model scores each failure: `P(recover)`, the **optimal retry time** (day-of-week × hour, salary-cycle aware), and expected time-to-recover.
3. **Decide** — a contextual-bandit **policy** picks the action per customer to maximise *expected recovered revenue*: retry-now, retry-at-best-slot, switch payment method, dunning nudge, request card update, or offer a grace link.
4. **Act** — generate a **personalised, multilingual dunning message** (Claude, with a deterministic fallback) and attach a **real Razorpay test-mode Payment Link** for one-tap recovery; dispatch on the best channel (email / WhatsApp / SMS).
5. **Measure** — a simulator + **held-out evaluation** proves the uplift in recovery rate and rupees recovered versus naive baselines. Every decision is logged as an explainable **agent trace**.

## Why this wins Track 3

| Judging signal | How we hit it |
|---|---|
| *"Something real, measured on a held-out test set"* (the buildathon's stated bar) | Frozen holdout, engine vs. **4** fair baselines (incl. a window-matched retrier) — *and* an **off-policy (IPS / Doubly-Robust) evaluation** that proves the lift counterfactually from logged data, the way Adyen/Stripe validate before deploy. |
| Genuine AI, not a CRUD dunning tool | Trained ML for recovery-probability + optimal-timing, a learning bandit (Thompson + a LinUCB contextual bandit), and an LLM dunning writer — each carrying its weight. |
| Defensible architecture | **Fail-closed** signed webhooks, idempotent event handling, a **durable SQLite store** (cases + persisted learning), and a **scheduler that actually executes** the chosen retry/nudge at the compliant time. |
| **India-native** (what a Stripe clone can't claim) | Salary-cycle-aware retry timing, UPI-autopay mandate handling, Hindi/regional dunning — **enforced** by a compliance layer (RBI 24h pre-debit notice, ₹15k AFA cap, TRAI DLT). |
| Uses Razorpay's own platform | Test-mode Customers, Orders, Payment Links, and webhooks; recovers a **real** test payment live in the demo. |

## Architecture

```
src/recovery/
├── domain/        Pydantic models + Razorpay-grounded failure taxonomy
├── simulation/    Synthetic subscription population + recovery environment (ground truth)
├── ml/            Feature engineering, P(recover) + optimal-timing models, training
├── policy/        EV orchestrator + Thompson bandit + LinUCB contextual bandit
├── llm/           Claude dunning-message generator (+ deterministic fallback)
├── razorpay/      Test-mode gateway + webhook verify (payments & subscriptions)
├── eval/          Baselines + held-out harness + off-policy (IPS/DR) evaluation
├── compliance.py  RBI e-mandate / UPI-Autopay / TRAI DLT guardrails
├── store.py       SQLite: durable cases + persisted bandit + scheduled jobs
├── scheduler.py   Executes retry/nudge jobs at the compliant time (closed loop)
├── live.py        Streaming live-campaign engine (SSE): engine vs baseline race
└── api/           FastAPI backend (webhooks, cases, metrics, live plan, SSE stream)
frontend/          React/Vite operating console (dark, CRED-inspired)
scripts/           generate_data · train_models · run_eval · robustness · demo_live
```

## Quickstart (development)

```bash
make install     # Python deps
make all         # simulate → train → eval  (runs with ZERO credentials)
make api         # API in dev on :8000 (reload)
make frontend    # Vite dev server on :5173 (proxies to the API)
```

No keys are required to run the full pipeline — the engine falls back to a faithful
mock gateway and a deterministic multilingual dunning writer. Add keys in `.env`
(see `.env.example`) to enable the **live** test-mode recovery demo and LLM-authored
messages. The LLM is used **only** for message copy (`LLM_PROVIDER` = `anthropic` /
`groq` / `openai`); evaluation always uses templates, so a key never changes the
measured results.

## Run it on a server (production)

One process serves the built React app **and** the API on a single port — no CORS, no
proxy, no separate frontend host.

```bash
# Option A — native
make install
make serve                      # builds frontend/dist, serves everything on :8000
#   → open http://<server>:8000  (HOST=0.0.0.0 by default; override PORT=... if needed)

# Option B — Docker (nothing to install but Docker)
docker compose up --build       # → http://localhost:8000
#   or: docker build -t revenue-recovery . && docker run -p 8000:8000 revenue-recovery
```

The trained models and held-out results are committed, so the container runs out of the
box; the population self-seeds on first start. Enable live features by passing env vars
(e.g. `docker run -p 8000:8000 -e LLM_PROVIDER=groq -e GROQ_API_KEY=... revenue-recovery`).
Behind a reverse proxy (nginx/Caddy), just forward to port 8000.

## Results

On **9,000 unseen failed recurring charges** (a held-out population the models never
trained on), every policy facing the *identical* hidden ground truth:

| Policy | Recovery rate | Revenue recovered | Retries used |
|---|---|---|---|
| No recovery (floor) | 0.0% | ₹0 | 0 |
| Fixed next-day retry *(Razorpay default)* | 47.1% | ₹63.5L | 26,361 |
| Fixed daily retry · 14-day window *(fair control)* | 58.4% | ₹78.1L | 67,499 |
| Fixed retry + channel/language-matched dunning | 56.8% | ₹75.9L | 24,385 |
| **AI Revenue Recovery engine** | **67.8%** | **₹91.1L** | **12,906** |

**+20.7 points (+44% relative) over the fixed-retry default, +₹27.5L recovered — with
roughly half the bank retries.** Crucially, it also beats a *window-matched* 14-day
retrier (58.4%) while using **5× fewer retries** (12.9k vs 67.5k), and beats a
*channel/language-matched* dunning baseline by +11.0 points — so the lift is genuine
timing + action skill, not a longer window or a rigged baseline. It wins biggest
exactly where a blind retry is useless:

| Failure class | Fixed retry | Engine |
|---|---|---|
| Expired card (needs update) | 8.6% | **65.6%** |
| Paused/revoked mandate (needs re-auth) | 12.6% | **64.4%** |
| Insufficient funds | 58.5% | **74.0%** |

**Proven counterfactually.** The lift isn't just an in-sim A/B — an off-policy
evaluation estimates the engine's value from a *random logging policy's* logged data
(the way Adyen/Stripe validate before deploying): Doubly-Robust **34.3%** and SNIPS
**34.2%** track the true on-policy value **33.6%**, all far above the random baseline
**18.1%**. See [`docs/RESULTS.md`](docs/RESULTS.md).

![Dashboard](docs/dashboard.png)

Numbers are reproduced by `make eval` on seed `9999`; full methodology and the
bandit's learned policy are in [`docs/RESULTS.md`](docs/RESULTS.md).

## Documentation

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — how each stage works and why.
- [`docs/RESULTS.md`](docs/RESULTS.md) — evaluation methodology + measured uplift.
- [`docs/PITCH.md`](docs/PITCH.md) — the 5-minute pitch + demo runbook.

---

<div align="center">
<sub>Built for the Razorpay AI Buildathon 2026 · Track 3 · Simulation-first, credential-optional.</sub>
</div>
