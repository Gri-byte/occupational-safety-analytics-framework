"""
Unit tests for data_processor.IncidentDataProcessor and helpers.
"""

import os
import sys
import tempfile
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from data_processor import (  # noqa: E402
    IncidentDataProcessor,
    QualityReport,
    VALID_SEVERITIES,
    run_pipeline,
)

DATA_PATH = ROOT / "data" / "raw_incidents.csv"


def _write_csv(df: pd.DataFrame) -> str:
    f = tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w", encoding="utf-8")
    df.to_csv(f, index=False)
    f.close()
    return f.name


def _make_valid_df(**overrides) -> pd.DataFrame:
    base = {
        "incident_id": ["INC-001", "INC-002", "INC-003"],
        "incident_date": ["2024-01-01", "2024-02-01", "2023-06-15"],
        "site_name": ["Site A"] * 3,
        "industry": ["mining"] * 3,
        "severity": ["Near Miss", "First Aid", "Lost Time Injury"],
        "incident_type": ["Slip/Trip/Fall"] * 3,
        "root_cause": ["Equipment failure"] * 3,
        "equipment_involved": ["Crane"] * 3,
        "worker_age": [30, 40, 50],
        "worker_tenure_years": [2.0, 5.0, 8.0],
        "days_lost": [0, 0, 5],
        "corrective_action": ["Action taken"] * 3,
        "reported_within_24h": [True, True, False],
        "latitude": [-38.45] * 3,
        "longitude": [-68.85] * 3,
        "province": ["Neuquen"] * 3,
        "country": ["AR"] * 3,
        "worker_gender": ["M"] * 3,
        "shift": ["Day"] * 3,
    }
    base.update(overrides)
    return pd.DataFrame(base)


class TestQualityReport:
    def test_zero_records_gives_zero_score(self):
        assert QualityReport().quality_score() == 0.0

    def test_perfect_data_gives_high_score(self):
        assert QualityReport(total_records=100).quality_score() == 100.0

    def test_score_decreases_with_issues(self):
        clean = QualityReport(total_records=100)
        dirty = QualityReport(total_records=100, duplicate_records=10,
                               missing_by_column={"col": 5})
        assert dirty.quality_score() < clean.quality_score()

    def test_score_never_below_zero(self):
        r = QualityReport(total_records=10, duplicate_records=100,
                          missing_by_column={"a": 100, "b": 100})
        assert r.quality_score() >= 0.0

    def test_summary_has_correct_shape(self):
        df = QualityReport(total_records=50).summary()
        assert list(df.columns) == ["Metric", "Value"]
        assert len(df) == 9


class TestOutlierDetection:
    def test_iqr_single_extreme_value(self):
        s = pd.Series(list(range(20)) + [1000])
        assert 20 in IncidentDataProcessor.detect_outliers_iqr(s)

    def test_iqr_uniform_series_no_outliers(self):
        assert IncidentDataProcessor.detect_outliers_iqr(pd.Series([5] * 100)) == []

    def test_iqr_custom_k_changes_result(self):
        s = pd.Series([1, 2, 3, 4, 5, 20])
        strict = IncidentDataProcessor.detect_outliers_iqr(s, k=1.0)
        lenient = IncidentDataProcessor.detect_outliers_iqr(s, k=3.0)
        assert len(strict) >= len(lenient)

    def test_zscore_constant_series(self):
        assert IncidentDataProcessor.detect_outliers_zscore(pd.Series([7] * 20)) == []

    def test_zscore_single_extreme(self):
        s = pd.Series([10] * 50 + [9999])
        assert 50 in IncidentDataProcessor.detect_outliers_zscore(s)

    def test_zscore_empty_series(self):
        assert IncidentDataProcessor.detect_outliers_zscore(
            pd.Series([], dtype=float)
        ) == []


class TestDataLoading:
    def test_missing_file_raises_file_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            IncidentDataProcessor(tmp_path / "missing.csv").load()

    def test_missing_columns_raises_value_error(self, tmp_path):
        csv = tmp_path / "incomplete.csv"
        pd.DataFrame({"incident_id": [1], "incident_date": ["2024-01-01"]}).to_csv(
            csv, index=False
        )
        with pytest.raises(ValueError, match="missing required columns"):
            IncidentDataProcessor(csv).load()

    @pytest.mark.skipif(not DATA_PATH.exists(), reason="run generate_sample_data.py first")
    def test_load_real_data_has_records(self):
        assert len(IncidentDataProcessor(DATA_PATH).load()) > 0


class TestCleaningLogic:
    def test_duplicate_rows_removed(self):
        df = _make_valid_df()
        fname = _write_csv(pd.concat([df, df.iloc[[0]]], ignore_index=True))
        try:
            proc = IncidentDataProcessor(fname)
            proc.load()
            assert proc.clean_data().duplicated().sum() == 0
        finally:
            os.unlink(fname)

    def test_severity_normalization_applied(self):
        fname = _write_csv(_make_valid_df(severity=["NEAR MISS", "MTC", "Lost Time Injury"]))
        try:
            proc = IncidentDataProcessor(fname)
            proc.load()
            clean = proc.clean_data()
            assert set(clean["severity"].unique()).issubset(set(VALID_SEVERITIES))
        finally:
            os.unlink(fname)

    def test_negative_days_zeroed(self):
        fname = _write_csv(_make_valid_df(days_lost=[0, -5, 3]))
        try:
            proc = IncidentDataProcessor(fname)
            proc.load()
            assert (proc.clean_data()["days_lost"] >= 0).all()
        finally:
            os.unlink(fname)

    def test_future_dates_removed(self):
        fname = _write_csv(
            _make_valid_df(incident_date=["2024-01-01", "2099-12-31", "2023-06-15"])
        )
        try:
            proc = IncidentDataProcessor(fname)
            proc.load()
            assert (proc.clean_data()["incident_date"] <= pd.Timestamp.today()).all()
        finally:
            os.unlink(fname)

    def test_missing_root_cause_filled(self):
        fname = _write_csv(
            _make_valid_df(root_cause=[None, "Equipment failure", "Fatigue / human error"])
        )
        try:
            proc = IncidentDataProcessor(fname)
            proc.load()
            assert proc.clean_data()["root_cause"].notna().all()
        finally:
            os.unlink(fname)


class TestIntegration:
    @pytest.mark.skipif(not DATA_PATH.exists(), reason="run generate_sample_data.py first")
    def test_run_pipeline_returns_clean_df_and_report(self):
        clean, report = run_pipeline(DATA_PATH)
        assert isinstance(clean, pd.DataFrame)
        assert isinstance(report, QualityReport)
        assert len(clean) > 0
        assert report.total_records > 0

    @pytest.mark.skipif(not DATA_PATH.exists(), reason="run generate_sample_data.py first")
    def test_kpis_are_complete(self):
        proc = IncidentDataProcessor(DATA_PATH)
        proc.load()
        proc.clean_data()
        kpis = proc.kpis()
        for key in ("total_incidents", "lost_time_injuries", "fatalities",
                    "lifter", "avg_days_lost", "pct_reported_24h",
                    "top_incident_type", "top_root_cause"):
            assert key in kpis