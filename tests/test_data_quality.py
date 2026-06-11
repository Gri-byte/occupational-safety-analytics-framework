"""
Test suite for the Occupational Safety Analytics Framework.

Run with:
    pytest tests/ -v
"""

import sys
from pathlib import Path

import pandas as pd
import pytest

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE / "src"))

from data_processor import (  # noqa: E402
    IncidentDataProcessor, run_pipeline, VALID_SEVERITIES,
)
from validation_rules import ComplianceValidator  # noqa: E402

DATA_PATH = BASE / "data" / "raw_incidents.csv"


# ---------------------------------------------------------------- fixtures
@pytest.fixture(scope="module")
def processor():
    proc = IncidentDataProcessor(DATA_PATH)
    proc.load()
    proc.profile()
    proc.clean_data()
    return proc


@pytest.fixture(scope="module")
def clean_df(processor):
    return processor.clean


@pytest.fixture(scope="module")
def validator(clean_df):
    v = ComplianceValidator(clean_df)
    v.run_all()
    return v


# ----------------------------------------------------------- data loading
class TestDataLoading:
    def test_raw_file_exists(self):
        assert DATA_PATH.exists(), "Run src/generate_data.py first"

    def test_raw_has_records(self, processor):
        assert len(processor.raw) > 500

    def test_required_columns_present(self, processor):
        required = {
            "incident_id", "incident_date", "site_name", "severity",
            "root_cause", "equipment_involved", "worker_age", "days_lost",
            "corrective_action", "latitude", "longitude",
        }
        assert required.issubset(processor.raw.columns)


# -------------------------------------------------------- quality profiling
class TestQualityProfiling:
    def test_detects_duplicates_in_raw(self, processor):
        assert processor.report.duplicate_records > 0

    def test_detects_missing_values(self, processor):
        assert sum(processor.report.missing_by_column.values()) > 0

    def test_detects_invalid_dates(self, processor):
        assert processor.report.invalid_dates > 0

    def test_detects_nonstandard_severities(self, processor):
        assert processor.report.invalid_severities > 0

    def test_quality_score_in_range(self, processor):
        score = processor.report.quality_score()
        assert 0 <= score <= 100


# ----------------------------------------------------------- outlier methods
class TestOutlierDetection:
    def test_iqr_finds_planted_outliers(self):
        series = pd.Series([1, 2, 3, 2, 3, 1, 2, 3, 2, 100])
        idx = IncidentDataProcessor.detect_outliers_iqr(series)
        assert 9 in idx

    def test_zscore_finds_extreme_value(self):
        series = pd.Series([10] * 30 + [500])
        idx = IncidentDataProcessor.detect_outliers_zscore(series)
        assert 30 in idx

    def test_zscore_handles_constant_series(self):
        series = pd.Series([5, 5, 5, 5])
        assert IncidentDataProcessor.detect_outliers_zscore(series) == []

    def test_raw_days_lost_has_outliers(self, processor):
        assert len(processor.report.outliers_iqr["days_lost"]) > 0


# --------------------------------------------------------------- cleaning
class TestCleaning:
    def test_no_duplicates_after_cleaning(self, clean_df):
        assert clean_df.duplicated().sum() == 0

    def test_severities_normalized(self, clean_df):
        assert set(clean_df["severity"].unique()).issubset(set(VALID_SEVERITIES))

    def test_no_future_dates(self, clean_df):
        assert (clean_df["incident_date"] <= pd.Timestamp.today()).all()

    def test_no_negative_days_lost(self, clean_df):
        assert (clean_df["days_lost"] >= 0).all()

    def test_worker_ages_legal(self, clean_df):
        ages = clean_df["worker_age"].dropna()
        assert ages.between(18, 70).all()

    def test_no_missing_root_cause(self, clean_df):
        assert clean_df["root_cause"].notna().all()

    def test_cleaning_preserves_majority_of_data(self, processor):
        retention = len(processor.clean) / len(processor.raw)
        assert retention > 0.90


# ------------------------------------------------------------------- KPIs
class TestKPIs:
    def test_kpis_structure(self, processor):
        kpis = processor.kpis()
        for key in ("total_incidents", "ltifr", "avg_days_lost",
                    "top_root_cause"):
            assert key in kpis

    def test_monthly_trend_has_moving_average(self, processor):
        trend = processor.monthly_trend()
        assert "moving_avg_3m" in trend.columns
        assert len(trend) > 12

    def test_pareto_cumulative_reaches_100(self, processor):
        pareto = processor.root_cause_pareto()
        assert pareto["cumulative_pct"].iloc[-1] == pytest.approx(100, abs=0.2)


# ------------------------------------------------------------- compliance
class TestComplianceRules:
    def test_all_rules_executed(self, validator):
        assert len(validator.results) == 10

    def test_critical_rules_pass_on_clean_data(self, validator):
        critical = [r for r in validator.results if r.severity == "critical"]
        failing = [r.rule_id for r in critical if not r.passed]
        assert not failing, f"Critical rules failing on clean data: {failing}"

    def test_compliance_rate_in_range(self, validator):
        assert 0 <= validator.compliance_rate() <= 100

    def test_future_date_rule_catches_violation(self, clean_df):
        bad = clean_df.head(5).copy()
        bad.loc[bad.index[0], "incident_date"] = pd.Timestamp("2030-01-01")
        result = ComplianceValidator(bad).rule_no_future_dates()
        assert not result.passed
        assert result.violations == 1

    def test_negative_days_rule_catches_violation(self, clean_df):
        bad = clean_df.head(5).copy()
        bad.loc[bad.index[0], "days_lost"] = -5
        result = ComplianceValidator(bad).rule_no_negative_days_lost()
        assert not result.passed
