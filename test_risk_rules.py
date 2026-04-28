import pytest
from risk_rules import label_risk, score_transaction


# A transaction with zero contribution from every scoring signal.
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


# ===========================================================================
# label_risk — exact boundary values
# ===========================================================================

class TestLabelThresholds:
    def test_zero_is_low(self):
        assert label_risk(0) == "low"

    def test_top_of_low(self):
        assert label_risk(29) == "low"

    def test_bottom_of_medium(self):
        assert label_risk(30) == "medium"

    def test_top_of_medium(self):
        assert label_risk(59) == "medium"

    def test_bottom_of_high(self):
        assert label_risk(60) == "high"

    def test_100_is_high(self):
        assert label_risk(100) == "high"


# ===========================================================================
# Per-signal exact scores — pin the scoring contract at every threshold
# ===========================================================================

class TestDeviceRiskScore:
    def test_below_lower_tier_scores_zero(self):
        assert score_transaction(tx(device_risk_score=39)) == 0

    def test_at_lower_tier_scores_10(self):
        assert score_transaction(tx(device_risk_score=40)) == 10

    def test_top_of_lower_tier_scores_10(self):
        assert score_transaction(tx(device_risk_score=69)) == 10

    def test_at_upper_tier_scores_25(self):
        assert score_transaction(tx(device_risk_score=70)) == 25

    def test_max_value_scores_25(self):
        assert score_transaction(tx(device_risk_score=100)) == 25


class TestAmountUsd:
    def test_below_lower_tier_scores_zero(self):
        assert score_transaction(tx(amount_usd=499)) == 0

    def test_at_lower_tier_scores_10(self):
        assert score_transaction(tx(amount_usd=500)) == 10

    def test_top_of_lower_tier_scores_10(self):
        assert score_transaction(tx(amount_usd=999)) == 10

    def test_at_upper_tier_scores_25(self):
        assert score_transaction(tx(amount_usd=1000)) == 25

    def test_very_large_amount_scores_25(self):
        assert score_transaction(tx(amount_usd=50000)) == 25


class TestVelocity24h:
    def test_below_lower_tier_scores_zero(self):
        assert score_transaction(tx(velocity_24h=2)) == 0

    def test_at_lower_tier_scores_5(self):
        assert score_transaction(tx(velocity_24h=3)) == 5

    def test_top_of_lower_tier_scores_5(self):
        assert score_transaction(tx(velocity_24h=5)) == 5

    def test_at_upper_tier_scores_20(self):
        assert score_transaction(tx(velocity_24h=6)) == 20

    def test_extreme_velocity_scores_20(self):
        assert score_transaction(tx(velocity_24h=50)) == 20


class TestFailedLogins24h:
    def test_below_lower_tier_scores_zero(self):
        assert score_transaction(tx(failed_logins_24h=1)) == 0

    def test_at_lower_tier_scores_10(self):
        assert score_transaction(tx(failed_logins_24h=2)) == 10

    def test_top_of_lower_tier_scores_10(self):
        assert score_transaction(tx(failed_logins_24h=4)) == 10

    def test_at_upper_tier_scores_20(self):
        assert score_transaction(tx(failed_logins_24h=5)) == 20

    def test_extreme_failures_scores_20(self):
        assert score_transaction(tx(failed_logins_24h=100)) == 20


class TestPriorChargebacks:
    def test_zero_chargebacks_scores_zero(self):
        assert score_transaction(tx(prior_chargebacks=0)) == 0

    def test_one_chargeback_scores_5(self):
        assert score_transaction(tx(prior_chargebacks=1)) == 5

    def test_two_chargebacks_scores_20(self):
        assert score_transaction(tx(prior_chargebacks=2)) == 20

    def test_many_chargebacks_scores_20(self):
        assert score_transaction(tx(prior_chargebacks=10)) == 20


class TestMerchantCategory:
    @pytest.mark.parametrize("cat", ["gift_cards", "crypto", "electronics", "wire_transfer"])
    def test_high_risk_merchant_scores_15(self, cat):
        assert score_transaction(tx(merchant_category=cat)) == 15

    def test_grocery_scores_zero(self):
        assert score_transaction(tx(merchant_category="grocery")) == 0

    def test_unlisted_merchant_scores_zero(self):
        assert score_transaction(tx(merchant_category="pet_supplies")) == 0

    def test_international_scores_15(self):
        assert score_transaction(tx(is_international=1)) == 15


class TestAccountAge:
    def test_very_new_account_scores_20(self):
        assert score_transaction(tx(account_age_days=1)) == 20

    def test_top_of_new_tier_scores_20(self):
        assert score_transaction(tx(account_age_days=29)) == 20

    def test_just_past_new_threshold_scores_10(self):
        # 30 days: not < 30, but < 90
        assert score_transaction(tx(account_age_days=30)) == 10

    def test_top_of_young_tier_scores_10(self):
        assert score_transaction(tx(account_age_days=89)) == 10

    def test_just_past_young_threshold_scores_zero(self):
        assert score_transaction(tx(account_age_days=90)) == 0

    def test_established_account_scores_zero(self):
        assert score_transaction(tx(account_age_days=500)) == 0


class TestKycLevel:
    def test_full_kyc_scores_zero(self):
        assert score_transaction(tx(kyc_level="full")) == 0

    def test_basic_kyc_scores_10(self):
        assert score_transaction(tx(kyc_level="basic")) == 10

    def test_no_kyc_scores_10(self):
        assert score_transaction(tx(kyc_level="none")) == 10


# ===========================================================================
# Missing optional fields — should not raise, should default to zero risk
# ===========================================================================

class TestMissingOptionalFields:
    def test_missing_merchant_category(self):
        t = {k: v for k, v in BASE_TX.items() if k != "merchant_category"}
        assert score_transaction(t) == 0

    def test_missing_account_age(self):
        # Default 999 → treated as established account
        t = {k: v for k, v in BASE_TX.items() if k != "account_age_days"}
        assert score_transaction(t) == 0

    def test_missing_kyc_level(self):
        t = {k: v for k, v in BASE_TX.items() if k != "kyc_level"}
        assert score_transaction(t) == 0

    def test_all_optional_fields_missing(self):
        required = {k: v for k, v in BASE_TX.items()
                    if k not in {"merchant_category", "account_age_days", "kyc_level"}}
        assert score_transaction(required) == 0


# ===========================================================================
# Score clamping
# ===========================================================================

class TestScoreBounds:
    def test_clean_transaction_scores_zero(self):
        assert score_transaction(BASE_TX) == 0

    def test_score_never_exceeds_100(self):
        all_signals = tx(
            device_risk_score=90, is_international=1, amount_usd=5000,
            velocity_24h=10, failed_logins_24h=10, prior_chargebacks=5,
            merchant_category="crypto", account_age_days=5, kyc_level="none",
        )
        assert score_transaction(all_signals) == 100

    def test_score_never_negative(self):
        assert score_transaction(BASE_TX) >= 0


# ===========================================================================
# Clearly fraudulent — every case should label "high"
# ===========================================================================

class TestClearlyFraudulent:
    def test_card_testing_pattern(self):
        """High velocity + high device risk + electronics purchase = card-testing ring.
        device=75 (+25) + velocity=8 (+20) + electronics (+15) = 60"""
        assert label_risk(score_transaction(tx(
            device_risk_score=75,
            velocity_24h=8,
            merchant_category="electronics",
        ))) == "high"

    def test_account_takeover_pattern(self):
        """Burst of failed logins then immediate large international purchase.
        failed=6 (+20) + intl (+15) + amount=1200 (+25) = 60"""
        assert label_risk(score_transaction(tx(
            failed_logins_24h=6,
            is_international=1,
            amount_usd=1200,
        ))) == "high"

    def test_new_account_gift_card_bust_out(self):
        """Brand-new account buying gift cards in bulk.
        age=10 (+20) + gift_cards (+15) + amount=1000 (+25) = 60"""
        assert label_risk(score_transaction(tx(
            account_age_days=10,
            merchant_category="gift_cards",
            amount_usd=1000,
        ))) == "high"

    def test_repeat_offender_with_velocity(self):
        """Multiple prior chargebacks + suspicious device + moderate burst.
        cb=2 (+20) + device=75 (+25) + amount=500 (+10) + velocity=3 (+5) = 60"""
        assert label_risk(score_transaction(tx(
            prior_chargebacks=2,
            device_risk_score=75,
            amount_usd=500,
            velocity_24h=3,
        ))) == "high"

    def test_international_crypto_from_new_account(self):
        """International crypto purchase from a week-old account.
        intl (+15) + crypto (+15) + age=7 (+20) + amount=1000 (+25) = 75"""
        assert label_risk(score_transaction(tx(
            is_international=1,
            merchant_category="crypto",
            account_age_days=7,
            amount_usd=1000,
        ))) == "high"

    def test_unverified_new_account_international_high_amount(self):
        """No KYC, new account, international large purchase.
        kyc (+10) + age=20 (+20) + intl (+15) + amount=1000 (+25) = 70"""
        assert label_risk(score_transaction(tx(
            kyc_level="none",
            account_age_days=20,
            is_international=1,
            amount_usd=1000,
        ))) == "high"

    def test_all_signals_firing(self):
        assert label_risk(score_transaction(tx(
            device_risk_score=85,
            is_international=1,
            amount_usd=1400,
            velocity_24h=8,
            failed_logins_24h=6,
            prior_chargebacks=3,
            merchant_category="gift_cards",
            account_age_days=20,
            kyc_level="basic",
        ))) == "high"


# ===========================================================================
# Clearly legitimate — every case should label "low"
# ===========================================================================

class TestClearlyLegitimate:
    def test_everyday_grocery_purchase(self):
        """Small domestic transaction on an established, fully-verified account."""
        assert label_risk(score_transaction(BASE_TX)) == "low"

    def test_streaming_subscription(self):
        assert label_risk(score_transaction(tx(
            amount_usd=14.99,
            merchant_category="streaming",
        ))) == "low"

    def test_large_purchase_from_trusted_account(self):
        """$1,000 on its own is only 25 points — clean account keeps it low."""
        assert label_risk(score_transaction(tx(amount_usd=1000))) == "low"

    def test_slightly_elevated_device_no_other_flags(self):
        """Device in the mid tier (+10) alone is not enough to reach medium."""
        assert label_risk(score_transaction(tx(device_risk_score=50))) == "low"

    def test_single_failed_login_no_other_flags(self):
        """One failed login is below the scoring threshold."""
        assert label_risk(score_transaction(tx(failed_logins_24h=1))) == "low"

    def test_young_account_small_domestic_purchase(self):
        """60-day-old account (+10) with a small purchase still scores low."""
        assert label_risk(score_transaction(tx(
            account_age_days=60,
            amount_usd=30,
        ))) == "low"

    def test_moderate_spend_domestic_vip_profile(self):
        """$400 domestic purchase on a two-year-old fully-verified account."""
        assert label_risk(score_transaction(tx(
            amount_usd=400,
            account_age_days=730,
            kyc_level="full",
        ))) == "low"


# ===========================================================================
# Borderline — scores land exactly at label boundaries
# ===========================================================================

class TestBorderlineCases:
    def test_exactly_at_medium_threshold(self):
        """amount=1000 (+25) + prior_cb=1 (+5) = 30 → medium, not low."""
        assert label_risk(score_transaction(tx(
            amount_usd=1000,
            prior_chargebacks=1,
        ))) == "medium"

    def test_one_point_below_medium(self):
        """amount=1000 (+25) alone = 25 → low."""
        assert label_risk(score_transaction(tx(amount_usd=1000))) == "low"

    def test_exactly_at_high_threshold(self):
        """device=70 (+25) + intl (+15) + amount=500 (+10) + vel=3 (+5) + cb=1 (+5) = 60 → high."""
        assert label_risk(score_transaction(tx(
            device_risk_score=70,
            is_international=1,
            amount_usd=500,
            velocity_24h=3,
            prior_chargebacks=1,
        ))) == "high"

    def test_one_signal_short_of_high(self):
        """Same as above minus prior_cb (+5) = 55 → medium, not high."""
        assert label_risk(score_transaction(tx(
            device_risk_score=70,
            is_international=1,
            amount_usd=500,
            velocity_24h=3,
        ))) == "medium"

    def test_new_account_risky_merchant_lands_medium(self):
        """age=10 (+20) + gift_cards (+15) = 35 → medium (needs big purchase to go high)."""
        assert label_risk(score_transaction(tx(
            account_age_days=10,
            merchant_category="gift_cards",
        ))) == "medium"

    def test_two_mid_tier_signals_land_medium(self):
        """device=50 (+10) + velocity=4 (+5) + amount=500 (+10) + logins=3 (+10) = 35 → medium."""
        assert label_risk(score_transaction(tx(
            device_risk_score=50,
            velocity_24h=4,
            amount_usd=500,
            failed_logins_24h=3,
        ))) == "medium"
