from __future__ import annotations

from typing import Dict


HIGH_RISK_MERCHANTS = {"gift_cards", "crypto", "electronics", "wire_transfer"}


def score_transaction(tx: Dict) -> int:
    """Return a fraud risk score from 0 to 100."""
    score = 0

    # High device risk signals a compromised or emulated device.
    if tx["device_risk_score"] >= 70:
        score += 25
    elif tx["device_risk_score"] >= 40:
        score += 10

    # International transactions have elevated fraud rates.
    if tx["is_international"] == 1:
        score += 15

    # High purchase amounts raise exposure.
    if tx["amount_usd"] >= 1000:
        score += 25
    elif tx["amount_usd"] >= 500:
        score += 10

    # High velocity in 24h is a strong card-testing / bust-out signal.
    if tx["velocity_24h"] >= 6:
        score += 20
    elif tx["velocity_24h"] >= 3:
        score += 5

    # Failed logins can signal an account takeover attempt.
    if tx["failed_logins_24h"] >= 5:
        score += 20
    elif tx["failed_logins_24h"] >= 2:
        score += 10

    # Prior chargeback history is the strongest predictor of future fraud.
    if tx["prior_chargebacks"] >= 2:
        score += 20
    elif tx["prior_chargebacks"] == 1:
        score += 5

    # Certain merchant categories are disproportionately targeted by fraudsters.
    if tx.get("merchant_category") in HIGH_RISK_MERCHANTS:
        score += 15

    # New accounts have less history to validate and are frequently used for fraud.
    account_age = tx.get("account_age_days", 999)
    if account_age < 30:
        score += 20
    elif account_age < 90:
        score += 10

    # Accounts without full KYC verification carry higher identity risk.
    if tx.get("kyc_level") in {"basic", "none"}:
        score += 10

    return max(0, min(score, 100))


def label_risk(score: int) -> str:
    if score >= 60:
        return "high"
    if score >= 30:
        return "medium"
    return "low"
