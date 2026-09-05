// Friendly display names that map onto the REAL engine vocabulary, so the
// story and the operating dashboard always agree.

export const ACTION_LABEL = {
  retry_now: "Retry now",
  retry_optimal: "Wait for the right moment",
  switch_method: "Switch payment method",
  dunning_nudge: "Send a reminder",
  request_card_update: "Request card update",
  offer_grace: "Offer a grace period",
  wait: "Hold",
  give_up: "Stop — unrecoverable",
};

export const CLASS_LABEL = {
  transient: "Temporary glitch",
  insufficient_funds: "Insufficient funds",
  soft_decline: "Soft decline",
  needs_card_update: "Card needs updating",
  needs_reauth: "Needs re-authorisation",
  hard_decline: "Unrecoverable",
  unknown: "Unknown",
};

export const actionLabel = (a) => ACTION_LABEL[a] || a;
export const classLabel = (c) => CLASS_LABEL[c] || c;

// ordering used across the app
export const POLICY_ORDER = [
  "no_action",
  "fixed_retry",
  "fixed_retry_14d",
  "generic_dunning",
  "engine",
];
export const POLICY_LABEL = {
  no_action: "No recovery",
  fixed_retry: "Fixed retry",
  fixed_retry_14d: "Fixed retry · 14d window",
  generic_dunning: "Retry + generic dunning",
  engine: "Rebound",
};
