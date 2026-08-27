# Architecture

How the engine is built, and why each choice makes the result **defensible** — the
thing a Razorpay panel will probe hardest.

## The loop

Every failed recurring charge flows through five stages:

<p align="center"><img src="diagrams/loop.svg" alt="The closed recovery loop — detect, predict, decide, act, measure, learn" width="860"></p>

<sub>*<a href="diagrams/loop.excalidraw">edit this diagram in Excalidraw</a>*</sub>

### 1 · Diagnose — `domain/taxonomy.py`
Raw Razorpay error `reason` codes are mapped to a **recoverability class**
(`transient`, `insufficient_funds`, `soft_decline`, `needs_card_update`,
`needs_reauth`, `hard_decline`). This is the single most predictive signal and it
decides which actions even make sense — you can't retry an expired card into
success, and you can't email a stolen-card decline back to life.

### 2 · Predict — `ml/`
Two gradient-boosted models over a shared feature vector (`ml/features.py`, used
identically at train and serve time so there's no skew):

- **RecoveryModel** — `P(this failure is recoverable)`, for triage and give-up.
- **TimingModel** — `P(a retry at slot t succeeds)`, scanned over the next 14 days
  × candidate hours to find the **optimal retry moment** per customer. This is our
  self-hosted, explainable take on "smart retries".

Both are trained purely on **observable** features (failure reason, instrument,
amount, tenure, estimated salary day). Latents that drive the ground truth (true
engagement, the real optimal hour) are **never** fed in — otherwise the eval would
be measuring leakage, not skill.

### 3 · Decide — `policy/engine.py` + `policy/bandit.py`
For each step the engine builds candidate actions and scores each by **expected
recovered rupees** = `P(success) × amount × delay-discount − message-cost`. A
**contextual bandit** (Thompson sampling over `class × action`) then corrects those
estimates from live outcomes — so if nudging `mandate_revoked` actually beats
retrying it, the policy learns that without retraining. The argmax wins; if nothing
clears the give-up floor, the case is dropped so no spend is wasted on dead cards.

### 4 · Act — `policy/executor.py` (+ `eval/`, `razorpay/`)
The engine only knows an **Executor Protocol** with two primitives — `retry` and
`nudge`. Swapping the executor swaps reality:

- `SimulatedExecutor` resolves against the hidden environment (for evaluation).
- `RazorpayExecutor` creates **real test-mode Payment Links** and schedules retries
  (for the live demo / API), with recovery confirmed asynchronously by webhooks.

Because the engine imports only the Protocol, it can never peek at ground truth.

### 5 · Measure — `eval/harness.py`
A frozen, unseen holdout is run through four policies against the **same** latents:
`no_action`, `fixed_retry` (Razorpay's default), `generic_dunning`, and `engine`.
The gap between them is attributable skill, not luck — see [RESULTS.md](RESULTS.md).

## Why the numbers are trustworthy

The hard part of a recovery project isn't the model — it's proving the lift is real.

- **A ground-truth simulator** (`simulation/environment.py`) assigns each failure
  hidden latents: a true recoverability ceiling, a real optimal retry hour, a
  funds-availability curve tied to the customer's salary day. Actions are resolved
  by sampling those latents (seeded, reproducible).
- **Observational training data** (`simulation/history.py`) is produced by a
  *randomised logging policy*, exactly like a messy real-world retry log. The models
  must learn the true structure from noisy observations — no oracle.
- **Held-out evaluation** uses a different seed, so customers and failures are
  unseen. Every policy faces identical latents, so differences are causal.
- **No leakage**: `recovery.ml` and `recovery.policy` never import
  `recovery.simulation.environment`. The engine sees only observable features.

## India-native by design
Salary-day-aware retry timing, a post-midnight auto-debit window, UPI-autopay and
e-mandate handling, WhatsApp-first channels, and Hindi/Hinglish/regional dunning.
These aren't cosmetic — the timing model rediscovers the payday windows from data,
and channel/language matching measurably lifts dunning conversion.

## Module map

| Package | Responsibility |
|---|---|
| `domain/` | Paise-accurate models + Razorpay failure taxonomy |
| `simulation/` | Population generator, latent environment, observational logs |
| `ml/` | Features, recovery + timing models, training |
| `policy/` | Bandit, expected-value orchestrator, executor Protocol |
| `llm/` | Claude / template dunning generation |
| `razorpay/` | Test-mode gateway, webhook verify/parse, live executor |
| `eval/` | Baselines + held-out harness |
| `api/` | FastAPI service (webhooks, metrics, cases, interactive plan) |
| `frontend/` | React analytics dashboard |
