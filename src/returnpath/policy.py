"""Fixed policy v1. Model/customer input is never a financial authority."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Decision:
    action: str
    reason: str


def decide(facts, authorized, operation, hold, now, *, original=10000, approved=3000):
    if hold:
        return Decision("REVIEW", "REVIEW_HOLD")
    if not authorized:
        return Decision("WAIT", "VERIFICATION_REQUIRED")
    if facts.get("warehouse") is None:
        return Decision("WAIT", "WAREHOUSE_UNKNOWN")
    if facts.get("warehouse") is not True:
        return Decision("WAIT", "WAREHOUSE_NOT_ACCEPTED")
    if facts.get("fetched_at") is None or now - facts["fetched_at"] > 30 or now < facts["fetched_at"]:
        return Decision("WAIT", "STALE_OBSERVATIONS")
    if facts.get("refunds") is None or facts.get("charge") is None:
        return Decision("WAIT", "PAYMENT_UNKNOWN")
    charge = facts["charge"]
    if (charge.get("livemode") is not False or charge.get("currency") != "usd"
        or charge.get("amount") != original or charge.get("paid") is not True
        or charge.get("captured") is not True or charge.get("disputed") is not False
        or charge.get("type") != "card" or charge.get("id") != facts.get("expected_charge")
        or type(facts.get("approved")) is not int or facts["approved"] != approved or type(approved) is not int or not 0 < approved <= original <= 100000):
        return Decision("REVIEW", "UNSUPPORTED_OR_CONFLICTING_FACTS")
    if facts["refunds"]:
        return Decision("REVIEW", "UNEXPECTED_REFUND")
    if operation and operation["first_attempt"] is not None:
        age = now - operation["first_attempt"]
        if age < 0 or age >= 23 * 3600 or operation["attempts"] >= 3:
            return Decision("REVIEW", "RETRY_BOUND_REACHED")
        if now < operation["next_attempt"]:
            return Decision("WAIT", "RETRY_BACKOFF")
    return Decision("POST", "FIXED_APPROVAL")
