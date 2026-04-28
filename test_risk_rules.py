from risk_rules import label_risk, score_transaction


BASE_TX = {
    "device_risk_score": 10,
    "is_international": 0,
    "amount_usd": 50,
    "velocity_24h": 1,
    "failed_logins_24h": 0,
    "prior_chargebacks": 0,
    "merchant_category": "grocery",
    "account_age_days": 500,
    "kyc_level": "full",
}


def tx(**overrides):
    return {**BASE_TX, **overrides}


# --- label thresholds ---

def test_label_risk_low():
    assert label_risk(10) == "low"
    assert label_risk(29) == "low"

def test_label_risk_medium():
    assert label_risk(30) == "medium"
    assert label_risk(59) == "medium"

def test_label_risk_high():
    assert label_risk(60) == "high"
    assert label_risk(100) == "high"


# --- individual signals add risk ---

def test_large_amount_adds_risk():
    assert score_transaction(tx(amount_usd=1200)) > score_transaction(tx(amount_usd=50))

def test_medium_amount_adds_risk():
    assert score_transaction(tx(amount_usd=600)) > score_transaction(tx(amount_usd=50))

def test_high_device_risk_adds_risk():
    assert score_transaction(tx(device_risk_score=75)) > score_transaction(tx(device_risk_score=10))

def test_mid_device_risk_adds_risk():
    assert score_transaction(tx(device_risk_score=50)) > score_transaction(tx(device_risk_score=10))

def test_international_adds_risk():
    assert score_transaction(tx(is_international=1)) > score_transaction(tx(is_international=0))

def test_high_velocity_adds_risk():
    assert score_transaction(tx(velocity_24h=8)) > score_transaction(tx(velocity_24h=1))

def test_medium_velocity_adds_risk():
    assert score_transaction(tx(velocity_24h=4)) > score_transaction(tx(velocity_24h=1))

def test_many_failed_logins_adds_risk():
    assert score_transaction(tx(failed_logins_24h=6)) > score_transaction(tx(failed_logins_24h=0))

def test_few_failed_logins_adds_risk():
    assert score_transaction(tx(failed_logins_24h=3)) > score_transaction(tx(failed_logins_24h=0))

def test_prior_chargebacks_add_risk():
    assert score_transaction(tx(prior_chargebacks=3)) > score_transaction(tx(prior_chargebacks=0))

def test_single_chargeback_adds_risk():
    assert score_transaction(tx(prior_chargebacks=1)) > score_transaction(tx(prior_chargebacks=0))

def test_high_risk_merchant_adds_risk():
    for cat in ("gift_cards", "crypto", "electronics", "wire_transfer"):
        assert score_transaction(tx(merchant_category=cat)) > score_transaction(tx(merchant_category="grocery")), cat

def test_new_account_adds_risk():
    assert score_transaction(tx(account_age_days=15)) > score_transaction(tx(account_age_days=500))

def test_young_account_adds_risk():
    assert score_transaction(tx(account_age_days=60)) > score_transaction(tx(account_age_days=500))

def test_basic_kyc_adds_risk():
    assert score_transaction(tx(kyc_level="basic")) > score_transaction(tx(kyc_level="full"))

def test_no_kyc_adds_risk():
    assert score_transaction(tx(kyc_level="none")) > score_transaction(tx(kyc_level="full"))


# --- extreme cases ---

def test_worst_case_fraudster_scores_high():
    fraudster = tx(
        device_risk_score=85,
        is_international=1,
        amount_usd=1400,
        velocity_24h=8,
        failed_logins_24h=6,
        prior_chargebacks=3,
        merchant_category="gift_cards",
        account_age_days=20,
        kyc_level="basic",
    )
    assert label_risk(score_transaction(fraudster)) == "high"

def test_clean_transaction_scores_low():
    assert label_risk(score_transaction(BASE_TX)) == "low"

def test_score_clamped_to_100():
    fraudster = tx(
        device_risk_score=90, is_international=1, amount_usd=5000,
        velocity_24h=10, failed_logins_24h=10, prior_chargebacks=5,
        merchant_category="crypto", account_age_days=5, kyc_level="none",
    )
    assert score_transaction(fraudster) == 100

def test_score_never_negative():
    assert score_transaction(BASE_TX) >= 0
