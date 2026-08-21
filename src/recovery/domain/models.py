"""Core domain models.

Money is stored in **paise** (integer) everywhere, matching Razorpay's API, and
formatted to ₹ only for display. Times are timezone-aware UTC; India-specific
signals (salary day, language) live on the customer where they belong.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


# --------------------------------------------------------------------------- #
# Enums
# --------------------------------------------------------------------------- #
class PaymentMethod(str, Enum):
    CARD = "card"
    UPI_AUTOPAY = "upi_autopay"
    EMANDATE = "emandate"
    NETBANKING = "netbanking"
    WALLET = "wallet"


class Channel(str, Enum):
    WHATSAPP = "whatsapp"
    EMAIL = "email"
    SMS = "sms"
    IN_APP = "in_app"
    NONE = "none"


class Language(str, Enum):
    EN = "en"
    HI = "hi"
    HINGLISH = "hinglish"
    TA = "ta"
    TE = "te"
    MR = "mr"
    KN = "kn"
    BN = "bn"


class RecoverabilityClass(str, Enum):
    """How a failure can be recovered — the axis that drives which action helps."""

    TRANSIENT = "transient"            # bank/gateway blip — retry soon, high odds
    INSUFFICIENT_FUNDS = "insufficient_funds"  # money will appear (salary day) — time the retry
    SOFT_DECLINE = "soft_decline"      # issuer said "not now" — retry later, medium odds
    NEEDS_CARD_UPDATE = "needs_card_update"    # expired/invalid — retry is futile until updated
    NEEDS_REAUTH = "needs_reauth"      # mandate paused/auth failed — customer must re-authorise
    HARD_DECLINE = "hard_decline"      # stolen/lost/fraud/closed — unrecoverable
    UNKNOWN = "unknown"


class ActionType(str, Enum):
    RETRY_NOW = "retry_now"
    RETRY_OPTIMAL = "retry_optimal"       # schedule a retry at the ML-predicted best slot
    SWITCH_METHOD = "switch_method"       # nudge customer onto an alternate instrument
    DUNNING_NUDGE = "dunning_nudge"       # message + payment link, no auto-retry
    REQUEST_CARD_UPDATE = "request_card_update"
    OFFER_GRACE = "offer_grace"           # grace period / partial offer to save the customer
    WAIT = "wait"                         # do nothing this step (let scheduled retry land)
    GIVE_UP = "give_up"                   # stop spending on an unrecoverable case


class CaseStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RECOVERED = "recovered"
    HALTED = "halted"        # exhausted attempts, still unpaid
    GAVE_UP = "gave_up"      # policy chose to stop


# --------------------------------------------------------------------------- #
# Entities
# --------------------------------------------------------------------------- #
def _now() -> datetime:
    return datetime.now(timezone.utc)


class Customer(BaseModel):
    id: str
    name: str = ""
    email: str = ""
    phone: str = ""
    city: str = ""
    language: Language = Language.EN
    preferred_channel: Channel = Channel.WHATSAPP
    tenure_months: int = 0
    lifetime_value_paise: int = 0
    # India-native signal: day-of-month the customer is typically paid.
    salary_day: int = 1
    # Latent-ish behavioural prior in [0,1]: how reliably this person pays once nudged.
    engagement: float = 0.5


class Subscription(BaseModel):
    id: str
    customer_id: str
    plan_name: str = "Pro"
    amount_paise: int = 49900
    interval: str = "monthly"
    method: PaymentMethod = PaymentMethod.CARD
    mandate_max_paise: int = 0
    created_at: datetime = Field(default_factory=_now)


class FailureEvent(BaseModel):
    """A single failed recurring charge — the trigger for a recovery case."""

    id: str
    subscription_id: str
    customer_id: str
    occurred_at: datetime
    amount_paise: int
    method: PaymentMethod
    reason_code: str
    attempt_number: int = 1
    # convenience denormalised fields carried from the gateway payload
    razorpay_payment_id: str | None = None
    razorpay_order_id: str | None = None


class RecoveryAction(BaseModel):
    type: ActionType
    channel: Channel = Channel.NONE
    scheduled_at: datetime | None = None
    executed_at: datetime | None = None
    language: Language = Language.EN
    message: str | None = None
    payment_link: str | None = None
    predicted_success: float | None = None
    succeeded: bool | None = None
    meta: dict = Field(default_factory=dict)


class RecoveryCase(BaseModel):
    id: str
    failure: FailureEvent
    customer: Customer
    subscription: Subscription
    status: CaseStatus = CaseStatus.OPEN
    recoverability_class: RecoverabilityClass = RecoverabilityClass.UNKNOWN
    predicted_recover_prob: float | None = None
    predicted_best_slot: str | None = None  # e.g. "Tue 10:00"
    actions: list[RecoveryAction] = Field(default_factory=list)
    trace: list[str] = Field(default_factory=list)
    recovered_at: datetime | None = None
    recovered_amount_paise: int = 0
    created_at: datetime = Field(default_factory=_now)

    def log(self, line: str) -> None:
        self.trace.append(line)


class RecoveryOutcome(BaseModel):
    case_id: str
    recovered: bool
    attempts: int
    revenue_recovered_paise: int = 0
    days_to_recover: float | None = None
    final_action: ActionType | None = None


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def format_inr(paise: int) -> str:
    """Format paise as an Indian-grouped rupee string, e.g. 149900 -> '₹1,499'."""
    rupees = paise / 100
    whole = int(rupees)
    frac = round(rupees - whole, 2)
    s = _indian_group(whole)
    if frac:
        return f"₹{s}.{int(round(frac * 100)):02d}"
    return f"₹{s}"


def _indian_group(n: int) -> str:
    neg = n < 0
    digits = str(abs(n))
    if len(digits) <= 3:
        grouped = digits
    else:
        head, tail = digits[:-3], digits[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        parts.insert(0, head)
        grouped = ",".join(parts) + "," + tail
    return ("-" if neg else "") + grouped
