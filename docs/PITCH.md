# Pitch & demo runbook

The 5-minute story, the live demo, and answers to the questions a Razorpay panel
will actually ask.

## The 5-minute pitch

**1 · The problem (45s).**
Subscription businesses lose 20–40% of recurring revenue to *involuntary* churn —
payments that fail for recoverable reasons: no balance on debit day, an expired
card, a bank blip, a paused UPI mandate. The customer never chose to leave. Today
the response is blunt: Razorpay retries next day at a fixed time, and the merchant
blasts one generic email. That recovers maybe half of what's recoverable.

**2 · The insight (30s).**
Two failures that look identical need opposite treatment. An *insufficient-funds*
failure is a *timing* problem — retry on salary day and it sails through. An
*expired-card* failure is futile to retry — it needs the customer to act. The
winning system diagnoses **why** each payment failed and picks the right action at
the right moment for the right customer.

**3 · What we built (60s).**
An agentic engine that runs a closed loop per failure — **Diagnose → Predict →
Decide → Act → Measure**. It maps the Razorpay error code to a recoverability
class, uses ML to predict the optimal retry slot and the recovery probability, a
contextual bandit to choose the action that maximises *expected recovered rupees*,
generates a personalised Hindi/Hinglish/English dunning message with a real
Razorpay Payment Link, and — crucially — **measures its own uplift on a held-out
test set**.

**4 · The result (45s).**
On 9,000 unseen failed charges, all policies facing identical ground truth:
**67.7% recovery vs 47.1% for the fixed-retry default — +20.6 points, +44%
relative, +₹26 lakh recovered — using roughly *half* the bank retries.** It wins
biggest exactly where a blind retry can't help: expired cards 8.6% → 65.6%,
paused mandates 12.6% → 64.4%.

**5 · Why it matters to Razorpay (30s).**
This is Agent Studio's revenue-recovery agent, made concrete, measurable, and
India-native. It plugs into existing Razorpay primitives — Subscriptions,
webhooks, Payment Links — and every decision is explainable, which is what a
payments company needs before it can automate money movement.

## Live demo runbook (2 minutes)

```bash
make install          # once
make all              # simulate → train → eval  (prints the uplift table)
make api              # terminal 1
make frontend         # terminal 2 → open http://localhost:5173
```

On the dashboard, in order:
1. **KPIs** — read the headline: 67.7% vs 47.1%, +44%, ₹ recovered, triage AUC.
2. **By failure class** — point at `needs_card_update` and `needs_reauth`: the blue
   (blind retry) bar is tiny, the green (engine) bar towers. "This is the money
   everyone else leaves on the table."
3. **Try the agent** — pick `card_expired`, language `hi`. Show it *refuses to
   retry*, chooses a card-update nudge, writes a Hindi message, and mints a payment
   link. Then switch to `insufficient_funds`, salary day 1 — show it schedules the
   retry for the payday morning window.
4. **Live stream** — click a case, read the reasoning trace aloud: diagnosis →
   timing model → chosen action → expected value. "Every rupee-moving decision is
   explainable."
5. **CLI demo (optional)** — `make demo` (or `python scripts/demo_live.py
   --reason insufficient_funds`) creates a **real** Razorpay test-mode Payment Link
   when keys are set.

## Anticipated panel questions

**"How do I know the uplift is real and not overfit?"**
The holdout uses a different random seed — unseen customers and failures. Every
policy is scored against the *same* hidden latents, so the gap is causal. Training
labels come from a noisy randomised logging policy, not an oracle. The ML never
sees the latent that drives outcomes (true engagement, the real optimal hour), so
there's no leakage — validation AUC is a believable 0.77/0.85, not a suspicious
0.99.

**"Why a bandit on top of the ML?"**
The ML predicts retry success well, but the *best action* for a class can drift
(issuer behaviour, mandate rules). The bandit corrects the engine's action beliefs
online from real outcomes without retraining, and it's transparent — you can read
the learned success rate per class → action.

**"Why does the engine take longer on average (4.5 vs 1.7 days)?"**
On purpose. For fund failures it *waits for payday* instead of burning retries on
an empty account. It recovers 20 points more with half the bank attempts — a few
days is the right trade for that, and it's a tunable knob (`delay_discount_days`).

**"Is the simulator hiding the hard part?"**
The simulator is the *evaluation*, not the product. The product is the diagnosis
taxonomy, the timing/recovery models, the EV+bandit policy, the multilingual
dunning, and the Razorpay integration — all of which run unchanged against real
`payment.failed` webhooks. The simulator exists so we can *prove* uplift, which
you can't do offline any other way.

**"What would production need?"**
Real historical failure data to retrain on, card-account-updater and network-token
integration, a proper scheduler/queue for retries, holdout A/B in live traffic,
and guardrails on message frequency. The architecture already separates decision
from execution (the Executor Protocol), so swapping the simulator for live
Razorpay is a one-class change.

## One-line summary
> A measurable, explainable, India-native recovery agent that turns Razorpay's
> failed recurring payments back into revenue — +44% over the default, on unseen data.
