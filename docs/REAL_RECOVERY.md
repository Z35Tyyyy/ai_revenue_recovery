# Activating the real Razorpay closed loop

The engine's **diagnose → predict → decide → act → measure** loop runs end-to-end in
the app already:

- The **Live** page streams a whole campaign through the engine in real time.
- The **Agent** page schedules a durable job and the **"Fast-forward the clock"**
  button fires pending jobs, confirming outcomes and letting the bandit learn — a
  *simulated* confirmation, clearly labelled.
- A background scheduler tick (`POST /api/scheduler/advance`, and an in-process loop)
  fires jobs whose time has come.

To close the loop with **real Razorpay events** — the undeniable version — expose the
webhook to the internet and let Razorpay drive it. All the code exists; these are the
manual, account-side steps.

## 1. Expose the local API

The API listens on `:8000`. Give Razorpay a public URL with a tunnel:

```bash
ngrok http 8000                 # → https://<id>.ngrok-free.app
# or:  cloudflared tunnel --url http://localhost:8000
```

## 2. Configure the webhook (Razorpay Dashboard → Settings → Webhooks → Add)

- **URL:** `https://<id>.ngrok-free.app/webhooks/razorpay`
- **Secret:** choose one, then set it for the API in `.env`:
  `RAZORPAY_WEBHOOK_SECRET=<your_secret>` and restart. The API verifies
  **HMAC-SHA256** over the raw body and **rejects** anything unsigned/invalid
  (fail-closed), so this is required.
- **Events:**
  - Recovery **triggers** → `payment.failed`, `subscription.pending`, `subscription.halted`
  - Recovery **confirmations** → `payment.captured`, `subscription.charged`

## 3. Drive a real recovery

1. A real failed recurring charge fires `payment.failed` / `subscription.pending` →
   the engine diagnoses it and creates a **real test-mode Payment Link** (with the
   case id embedded in the payment `notes`).
2. Pay that link in Razorpay test mode → Razorpay fires **`payment.captured`**
   carrying the same `notes.case_id` → the API's `confirm_recovery()` marks the case
   **recovered** and the bandit learns from the *real* outcome.

The loop is now closed by Razorpay, live on screen. Every handler is **idempotent**
(deduped on `x-razorpay-event-id`) and **fail-closed** on the signature, so it is safe
to point real test traffic at it.
