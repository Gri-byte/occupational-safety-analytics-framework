"""
Unit and edge-case tests for validation_rules.ComplianceValidator.
"""

import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from validation_rules import ComplianceValidator  # noqa: E402


def _patch(df: pd.DataFrame, **kwargs) -> pd.DataFrame:
    out = df.copy()
    for col, val in kwargs.items():
        out[col] = val
    return out


class TestR001UniqueIds:
    def test_passes_on_unique_ids(self, minimal_clean_df):
        result = ComplianceValidator(minimal_clean_df).rule_unique_incident_ids()
        assert result.passed
        assert result.violations == 0

    def test_fails_on_duplicate_ids(self, minimal_clean_df):
        df = minimal_clean_df.copy()
        df.loc[1, "incident_id"] = df.loc[0, "incident_id"]
        result = ComplianceValidator(df).rule_unique_incident_ids()
        assert not result.passed
        assert result.violations == 2

    def test_violation_indices_match(self, minimal_clean_df):
        df = minimal_clean_df.copy()
        df.loc[0, "incident_id"] = df.loc[1, "incident_id"]
        result = ComplianceValidator(df).rule_unique_incident_ids()
        assert set(result.violation_indices) == {0, 1}


class TestR002FutureDates:
    def test_passes_on_past_dates(self, minimal_clean_df):
        result = ComplianceValidator(minimal_clean_df).rule_no_future_dates()
        assert result.passed

    def test_fails_on_single_future_date(self, minimal_clean_df):
        df = minimal_clean_df.copy()
        df.loc[0, "incident_date"] = pd.Timestamp("2099-01-01")
        result = ComplianceValidator(df).rule_no_future_dates()
        assert not result.passed
        assert result.violations == 1

    def test_fails_on_nat(self, minimal_clean_df):
        df = minimal_clean_df.copy()
        df.loc[0, "incident_date"] = pd.NaT
        result = ComplianceValidator(df).rule_no_future_dates()
        assert not result.passed


class TestR003ValidSeverity:
    def test_passes_all_standard_values(self, minimal_clean_df):
        result = ComplianceValidator(minimal_clean_df).rule_valid_severity()
        assert result.passed

    @pytest.mark.parametrize(
        "bad_value",
        ["NEAR MISS", "MTC", "LTI", "fatal", "Unknown", ""],
    )
    def test_fails_on_non_standard(self, minimal_clean_df, bad_value):
        df = minimal_clean_df.copy()
        df.loc[0, "severity"] = bad_value
        result = ComplianceValidator(df).rule_valid_severity()
        assert not result.passed


class TestR004FatalitiesAction:
    def test_fatality_with_pending_action_fails(self, minimal_clean_df):
        df = minimal_clean_df.copy()
        fatality_idx = df[df["severity"] == "Fatality"].index
        df.loc[fatality_idx, "corrective_action"] = "Pending investigation"
        result = ComplianceValidator(df).rule_fatalities_require_action()
        assert not result.passed

    def test_fatality_with_real_action_passes(self, minimal_clean_df):
        df = minimal_clean_df.copy()
        fatality_idx = df[df["severity"] == "Fatality"].index
        df.loc[fatality_idx, "corrective_action"] = "Engineering control installed"
        result = ComplianceValidator(df).rule_fatalities_require_action()
        assert result.passed


class TestR005LTIDaysLost:
    def test_lti_with_zero_days_fails(self, minimal_clean_df):
        df = minimal_clean_df.copy()
        lti_idx = df[df["severity"] == "Lost Time Injury"].index
        df.loc[lti_idx, "days_lost"] = 0
        result = ComplianceValidator(df).rule_lti_requires_days_lost()
        assert not result.passed

    def test_lti_with_positive_days_passes(self, minimal_clean_df):
        df = minimal_clean_df.copy()
        lti_idx = df[df["severity"] == "Lost Time Injury"].index
        df.loc[lti_idx, "days_lost"] = 5
        result = ComplianceValidator(df).rule_lti_requires_days_lost()
        assert result.passed


class TestR006WorkerAge:
    @pytest.mark.parametrize("invalid_age", [15, 17, 71, 102, -1])
    def test_invalid_age_fails(self, minimal_clean_df, invalid_age):
        df = minimal_clean_df.copy()
        df.loc[0, "worker_age"] = invalid_age
        result = ComplianceValidator(df).rule_worker_age_legal()
        assert not result.passed

    def test_missing_age_is_ignored(self, minimal_clean_df):
        df = minimal_clean_df.copy()
        df.loc[0, "worker_age"] = float("nan")
        result = ComplianceValidator(df).rule_worker_age_legal()
        assert result.passed

    def test_boundary_ages_pass(self, minimal_clean_df):
        df = minimal_clean_df.copy()
        df.loc[0, "worker_age"] = 18
        df.loc[1, "worker_age"] = 70
        result = ComplianceValidator(df).rule_worker_age_legal()
        assert result.passed


class TestR007NegativeDays:
    def test_negative_days_fails(self, minimal_clean_df):
        df = minimal_clean_df.copy()
        df.loc[0, "days_lost"] = -1
        result = ComplianceValidator(df).rule_no_negative_days_lost()
        assert not result.passed

    def test_zero_days_passes(self, minimal_clean_df):
        result = ComplianceValidator(minimal_clean_df).rule_no_negative_days_lost()
        assert result.passed


class TestR008ReportingRate:
    def test_all_reported_passes(self, minimal_clean_df):
        df = _patch(minimal_clean_df, reported_within_24h=True)
        assert ComplianceValidator(df).rule_24h_reporting_rate(min_rate=0.85).passed

    def test_low_rate_fails(self, minimal_clean_df):
        df = _patch(minimal_clean_df, reported_within_24h=False)
        assert not ComplianceValidator(df).rule_24h_reporting_rate(min_rate=0.85).passed

    def test_custom_threshold_respected(self, minimal_clean_df):
        df = minimal_clean_df.copy()
        df["reported_within_24h"] = [True] * 7 + [False] * 3
        assert not ComplianceValidator(df).rule_24h_reporting_rate(min_rate=0.85).passed
        assert ComplianceValidator(df).rule_24h_reporting_rate(min_rate=0.50).passed


class TestR009RootCause:
    def test_missing_root_cause_on_serious_fails(self, minimal_clean_df):
        df = minimal_clean_df.copy()
        lti_idx = df[df["severity"] == "Lost Time Injury"].index[0]
        df.loc[lti_idx, "root_cause"] = None
        assert not ComplianceValidator(df).rule_root_cause_documented().passed

    def test_missing_root_cause_on_near_miss_passes(self, minimal_clean_df):
        df = minimal_clean_df.copy()
        nm_idx = df[df["severity"] == "Near Miss"].index[0]
        df.loc[nm_idx, "root_cause"] = None
        assert ComplianceValidator(df).rule_root_cause_documented().passed


class TestR010Coordinates:
    @pytest.mark.parametrize(
        "lat,lon",
        [(-91, 0), (91, 0), (0, -181), (0, 181), (200, 200)],
    )
    def test_invalid_coords_fail(self, minimal_clean_df, lat, lon):
        df = minimal_clean_df.copy()
        df.loc[0, "latitude"] = lat
        df.loc[0, "longitude"] = lon
        assert not ComplianceValidator(df).rule_location_coordinates_valid().passed


class TestRunAll:
    def test_run_all_returns_ten_rows(self, minimal_clean_df):
        assert len(ComplianceValidator(minimal_clean_df).run_all()) == 10

    def test_compliance_rate_without_explicit_run_all(self, minimal_clean_df):
        rate = ComplianceValidator(minimal_clean_df).compliance_rate()
        assert 0 <= rate <= 100

    def test_empty_dataframe_does_not_raise(self, empty_df):
        v = ComplianceValidator(empty_df)
        assert len(v.run_all()) == 10
        assert v.compliance_rate() >= 0