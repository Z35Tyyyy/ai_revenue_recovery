import { useEffect, useState } from "react";
import { api } from "../api.js";
import sampleCases from "./sampleCases.json";

// Mirrors the real held-out eval so the marketing story renders correctly even
// with the API offline. Live data replaces this whenever the backend responds.
export const FALLBACK_METRICS = {
  holdout: {
    engine_prediction_auc: 0.6623,
    uplift: {
      vs_fixed_retry: { recovery_rate_abs: 0.2074, recovery_rate_rel: 0.4409,
        revenue_recovered_delta_paise: 275498300 },
      vs_generic_dunning: { recovery_rate_abs: 0.1096, recovery_rate_rel: 0.1927,
        revenue_recovered_delta_paise: 151591400 },
    },
    bandit: {
      needs_card_update: { request_card_update: 0.24 },
      needs_reauth: { dunning_nudge: 0.228 },
      insufficient_funds: { retry_optimal: 0.326, retry_now: 0.289, dunning_nudge: 0.251 },
      soft_decline: { retry_optimal: 0.265, retry_now: 0.224, dunning_nudge: 0.192 },
      transient: { retry_now: 0.658, retry_optimal: 0.568 },
      hard_decline: { switch_method: 0.039 },
    },
    holdout: { customers: 6000, failures: 9000, seed: 9999 },
    offpolicy: {
      logging_policy_value: 0.1807,
      engine_onpolicy_value: 0.3362,
      estimates: { direct_method: 0.3089, ips: 0.354, snips: 0.3417, doubly_robust: 0.3427 },
      n: 4000,
      action_space: ["give_up", "retry_now", "retry_optimal", "nudge"],
    },
    policies: {
      no_action: { recovery_rate: 0, total: 9000, recovered: 0, revenue_recovered_paise: 0,
        revenue_total_paise: 1328480000, retries: 0, nudges: 0, avg_days_to_recover: null, by_class_rate: {} },
      fixed_retry: { recovery_rate: 0.4706, total: 9000, recovered: 4235, revenue_recovered_paise: 635021500,
        revenue_total_paise: 1328480000, retries: 26361, nudges: 0, avg_days_to_recover: 1.72,
        by_class_rate: { hard_decline: 0.0066, insufficient_funds: 0.5847, needs_card_update: 0.0863,
          needs_reauth: 0.1257, soft_decline: 0.6049, transient: 0.992 } },
      fixed_retry_14d: { recovery_rate: 0.5839, total: 9000, recovered: 5255, revenue_recovered_paise: 781009500,
        revenue_total_paise: 1328480000, retries: 67499, nudges: 0, avg_days_to_recover: 2.87,
        by_class_rate: { hard_decline: 0.0066, insufficient_funds: 0.7699, needs_card_update: 0.1384,
          needs_reauth: 0.1878, soft_decline: 0.7658, transient: 0.998 } },
      generic_dunning: { recovery_rate: 0.5684, total: 9000, recovered: 5116, revenue_recovered_paise: 758928400,
        revenue_total_paise: 1328480000, retries: 24385, nudges: 5664, avg_days_to_recover: 1.73,
        by_class_rate: { hard_decline: 0.0284, insufficient_funds: 0.6705, needs_card_update: 0.2917,
          needs_reauth: 0.3177, soft_decline: 0.6622, transient: 0.995 } },
      engine: { recovery_rate: 0.678, total: 9000, recovered: 6102, revenue_recovered_paise: 910519800,
        revenue_total_paise: 1328480000, retries: 12906, nudges: 8467, avg_days_to_recover: 4.41,
        by_class_rate: { hard_decline: 0.0306, insufficient_funds: 0.7399, needs_card_update: 0.6555,
          needs_reauth: 0.6438, soft_decline: 0.646, transient: 0.955 } },
    },
  },
  live_sample: null,
  bandit: {},
  real_recoveries: { count: 0, total_paise: 0, items: [] },
  capabilities: { razorpay_live: false, llm_enabled: false, llm_provider: null },
};

const FALLBACK_REASONS = [
  { code: "insufficient_funds", class: "insufficient_funds", retry_helps: true, prior_recover_prob: 0.62, description: "No balance on debit day." },
  { code: "card_expired", class: "needs_card_update", retry_helps: false, prior_recover_prob: 0.34, description: "Card on file expired." },
  { code: "mandate_paused", class: "needs_reauth", retry_helps: false, prior_recover_prob: 0.38, description: "UPI-autopay mandate paused." },
  { code: "do_not_honour", class: "soft_decline", retry_helps: true, prior_recover_prob: 0.48, description: "Issuer soft-declined." },
  { code: "issuer_unavailable", class: "transient", retry_helps: true, prior_recover_prob: 0.78, description: "Bank temporarily unreachable." },
  { code: "stolen_or_lost_card", class: "hard_decline", retry_helps: false, prior_recover_prob: 0.05, description: "Card reported stolen/lost." },
];

export function useMetrics() {
  const [metrics, setMetrics] = useState(null);
  const [live, setLive] = useState(false);
  useEffect(() => {
    let alive = true;
    api.metrics()
      .then((m) => alive && (setMetrics(m), setLive(true)))
      .catch(() => alive && (setMetrics(FALLBACK_METRICS), setLive(false)));
    return () => { alive = false; };
  }, []);
  return { metrics, live, loading: metrics === null };
}

export function useHealth() {
  const [health, setHealth] = useState(null);
  const [checked, setChecked] = useState(false);
  useEffect(() => {
    let alive = true;
    api.health()
      .then((h) => alive && (setHealth(h), setChecked(true)))
      .catch(() => alive && setChecked(true));
    return () => { alive = false; };
  }, []);
  return { health, checked, online: !!health };
}

export function useCases(params = {}) {
  const [data, setData] = useState({ cases: null, total: 0 });
  const [live, setLive] = useState(false);
  const key = JSON.stringify(params);
  useEffect(() => {
    const ctrl = new AbortController();
    let alive = true;
    api.cases(params)
      .then((d) => alive && (setData({ cases: d.cases, total: d.total }), setLive(true)))
      .catch((e) => {
        if (e?.name === "AbortError" || !alive) return;
        setData({ cases: sampleCases, total: sampleCases.length });
        setLive(false);
      });
    return () => { alive = false; ctrl.abort(); };
  }, [key]); // eslint-disable-line react-hooks/exhaustive-deps
  return { cases: data.cases, total: data.total, live, loading: data.cases === null };
}

export function useReasons() {
  const [reasons, setReasons] = useState(FALLBACK_REASONS);
  useEffect(() => {
    let alive = true;
    api.reasons()
      .then((d) => alive && d?.reasons?.length && setReasons(d.reasons))
      .catch(() => {});
    return () => { alive = false; };
  }, []);
  return reasons;
}
