import { useEffect, useState } from "react";
import { api } from "../api.js";

// Mirrors the real held-out eval so the marketing story renders correctly even
// with the API offline. Live data replaces this whenever the backend responds.
export const FALLBACK_METRICS = {
  holdout: {
    engine_prediction_auc: 0.6644,
    uplift: {
      vs_fixed_retry: { recovery_rate_abs: 0.206, recovery_rate_rel: 0.4378,
        revenue_recovered_delta_paise: 264419600 },
    },
    bandit: {
      needs_card_update: { request_card_update: 0.24 },
      needs_reauth: { dunning_nudge: 0.228 },
      insufficient_funds: { retry_optimal: 0.326, retry_now: 0.289, dunning_nudge: 0.251 },
      soft_decline: { retry_optimal: 0.265, retry_now: 0.224, dunning_nudge: 0.192 },
      transient: { retry_now: 0.658, retry_optimal: 0.568 },
      hard_decline: { switch_method: 0.039 },
    },
    policies: {
      no_action: { recovery_rate: 0, total: 9000, recovered: 0, revenue_recovered_paise: 0,
        revenue_total_paise: 1328480000, retries: 0, nudges: 0, avg_days_to_recover: null, by_class_rate: {} },
      fixed_retry: { recovery_rate: 0.4706, total: 9000, recovered: 4235, revenue_recovered_paise: 635021500,
        revenue_total_paise: 1328480000, retries: 26361, nudges: 0, avg_days_to_recover: 1.7,
        by_class_rate: { hard_decline: 0.0066, insufficient_funds: 0.5847, needs_card_update: 0.0863,
          needs_reauth: 0.1257, soft_decline: 0.6049, transient: 0.992 } },
      generic_dunning: { recovery_rate: 0.5317, total: 9000, recovered: 4785, revenue_recovered_paise: 720116500,
        revenue_total_paise: 1328480000, retries: 25122, nudges: 5664, avg_days_to_recover: 1.7,
        by_class_rate: { hard_decline: 0.0079, insufficient_funds: 0.63, needs_card_update: 0.33,
          needs_reauth: 0.27, soft_decline: 0.62, transient: 0.98 } },
      engine: { recovery_rate: 0.6766, total: 9000, recovered: 6089, revenue_recovered_paise: 899441100,
        revenue_total_paise: 1328480000, retries: 13012, nudges: 8163, avg_days_to_recover: 4.5,
        by_class_rate: { hard_decline: 0.0175, insufficient_funds: 0.7373, needs_card_update: 0.6555,
          needs_reauth: 0.6438, soft_decline: 0.6468, transient: 0.953 } },
    },
  },
  live_sample: null,
  bandit: {},
  capabilities: { razorpay_live: false, llm_enabled: false, llm_provider: null },
};

export function useMetrics() {
  const [metrics, setMetrics] = useState(null);
  const [live, setLive] = useState(false);

  useEffect(() => {
    let alive = true;
    api
      .metrics()
      .then((m) => alive && (setMetrics(m), setLive(true)))
      .catch(() => alive && (setMetrics(FALLBACK_METRICS), setLive(false)));
    return () => {
      alive = false;
    };
  }, []);

  return { metrics, live, loading: metrics === null };
}

export function useHealth() {
  const [health, setHealth] = useState(null);
  useEffect(() => {
    let alive = true;
    api.health().then((h) => alive && setHealth(h)).catch(() => {});
    return () => { alive = false; };
  }, []);
  return health;
}
