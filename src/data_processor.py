"""
HSE Data Processing Pipeline
=============================
Data profiling, quality assessment, outlier detection (IQR & Z-score),
and trend analysis for occupational safety incident data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

VALID_SEVERITIES = ["Near Miss", "First Aid", "Medical Treatment",
                    "Lost Time Injury", "Fatality"]

SEVERITY_NORMALIZATION = {
    "NEAR MISS": "Near Miss",
    "FIRST AID": "First Aid",
    "MEDICAL TREATMENT": "Medical Treatment",
    "MTC": "Medical Treatment",
    "LOST TIME INJURY": "Lost Time Injury",
    "LTI": "Lost Time Injury",
    "FATALITY": "Fatality",
}


@dataclass
class QualityReport:
    """Container for data quality assessment results."""
    total_records: int = 0
    duplicate_records: int = 0
    missing_by_column: dict = field(default_factory=dict)
    outliers_iqr: dict = field(default_factory=dict)
    outliers_zscore: dict = field(default_factory=dict)
    invalid_dates: int = 0
    invalid_severities: int = 0
    negative_values: dict = field(default_factory=dict)

    def quality_score(self) -> float:
        """Overall quality score 0-100 (simple weighted heuristic)."""
        if self.total_records == 0:
            return 0.0
        issues = (
            self.duplicate_records
            + sum(self.missing_by_column.values())
            + sum(len(v) for v in self.outliers_iqr.values())
            + self.invalid_dates
            + self.invalid_severities
            + sum(self.negative_values.values())
        )
        return round(max(0.0, 100 * (1 - issues / (self.total_records * 3))), 1)

    def summary(self) -> pd.DataFrame:
        rows = [
            ("Total records", self.total_records),
            ("Duplicate records", self.duplicate_records),
            ("Missing values (total)", sum(self.missing_by_column.values())),
            ("IQR outliers (total)", sum(len(v) for v in self.outliers_iqr.values())),
            ("Z-score outliers (total)", sum(len(v) for v in self.outliers_zscore.values())),
            ("Invalid dates", self.invalid_dates),
            ("Non-standard severities", self.invalid_severities),
            ("Negative numeric values", sum(self.negative_values.values())),
            ("Quality score", f"{self.quality_score()}/100"),
        ]
        return pd.DataFrame(rows, columns=["Metric", "Value"])


class IncidentDataProcessor:
    """Loads, profiles, validates, and cleans HSE incident data."""

    NUMERIC_COLS = ["worker_age", "worker_tenure_years", "days_lost"]

    def __init__(self, csv_path: str | Path):
        self.csv_path = Path(csv_path)
        self.raw: pd.DataFrame | None = None
        self.clean: pd.DataFrame | None = None
        self.report = QualityReport()

    # ------------------------------------------------------------------ load
    def load(self) -> pd.DataFrame:
        self.raw = pd.read_csv(self.csv_path)
        self.report.total_records = len(self.raw)
        return self.raw

    # --------------------------------------------------------------- profile
    def profile(self) -> QualityReport:
        if self.raw is None:
            self.load()
        df = self.raw

        self.report.duplicate_records = int(df.duplicated().sum())
        self.report.missing_by_column = {
            c: int(n) for c, n in df.isna().sum().items() if n > 0
        }

        for col in self.NUMERIC_COLS:
            series = pd.to_numeric(df[col], errors="coerce").dropna()
            self.report.outliers_iqr[col] = self.detect_outliers_iqr(series)
            self.report.outliers_zscore[col] = self.detect_outliers_zscore(series)
            neg = int((series < 0).sum())
            if neg:
                self.report.negative_values[col] = neg

        dates = pd.to_datetime(df["incident_date"], errors="coerce")
        today = pd.Timestamp.today().normalize()
        self.report.invalid_dates = int((dates.isna() | (dates > today)).sum())

        self.report.invalid_severities = int(
            (~df["severity"].isin(VALID_SEVERITIES)).sum()
        )
        return self.report

    # ------------------------------------------------------------- outliers
    @staticmethod
    def detect_outliers_iqr(series: pd.Series, k: float = 1.5) -> list[int]:
        """Return index list of IQR outliers."""
        q1, q3 = series.quantile([0.25, 0.75])
        iqr = q3 - q1
        lower, upper = q1 - k * iqr, q3 + k * iqr
        mask = (series < lower) | (series > upper)
        return series[mask].index.tolist()

    @staticmethod
    def detect_outliers_zscore(series: pd.Series, threshold: float = 3.0) -> list[int]:
        """Return index list of Z-score outliers."""
        std = series.std()
        if std == 0 or np.isnan(std):
            return []
        z = (series - series.mean()) / std
        return series[z.abs() > threshold].index.tolist()

    # ---------------------------------------------------------------- clean
    def clean_data(self) -> pd.DataFrame:
        """Apply cleaning: dedupe, normalize severities, fix invalid values."""
        if self.raw is None:
            self.load()
        df = self.raw.copy()

        # 1. Remove exact duplicates, then partial duplicates by incident_id
        df = df.drop_duplicates().reset_index(drop=True)
        df = df.drop_duplicates(subset=["incident_id"], keep="first").reset_index(drop=True)

        # 2. Normalize severity labels
        df["severity"] = df["severity"].replace(SEVERITY_NORMALIZATION)
        df = df[df["severity"].isin(VALID_SEVERITIES)]

        # 3. Parse dates, drop impossible ones
        df["incident_date"] = pd.to_datetime(df["incident_date"], errors="coerce")
        today = pd.Timestamp.today().normalize()
        df = df[df["incident_date"].notna() & (df["incident_date"] <= today)]

        # 4. Fix numeric ranges
        df.loc[df["days_lost"] < 0, "days_lost"] = 0
        df = df[(df["worker_age"].isna()) | df["worker_age"].between(18, 70)]

        # 5. Fill categorical missing values
        df["root_cause"] = df["root_cause"].fillna("Under investigation")
        df["corrective_action"] = df["corrective_action"].fillna("Pending investigation")
        df["equipment_involved"] = df["equipment_involved"].fillna("Not specified")

        self.clean = df.reset_index(drop=True)
        return self.clean

    # ---------------------------------------------------------------- KPIs
    def kpis(self) -> dict:
        """Core HSE KPIs computed from cleaned data."""
        df = self.clean if self.clean is not None else self.clean_data()
        total = len(df)
        lti = int((df["severity"] == "Lost Time Injury").sum())
        fatalities = int((df["severity"] == "Fatality").sum())

        # Assume 200,000 hours base (OSHA standard) and a fixed workforce proxy
        hours_worked = total * 2000  # proxy: each incident maps to exposure
        ltifr = round(lti * 1_000_000 / hours_worked, 2) if hours_worked else 0

        return {
            "total_incidents": total,
            "lost_time_injuries": lti,
            "fatalities": fatalities,
            "ltifr": ltifr,
            "avg_days_lost": round(float(df["days_lost"].mean()), 1),
            "pct_reported_24h": round(100 * df["reported_within_24h"].mean(), 1),
            "top_incident_type": df["incident_type"].mode().iat[0],
            "top_root_cause": df["root_cause"].mode().iat[0],
        }

    # --------------------------------------------------------------- trends
    def monthly_trend(self) -> pd.DataFrame:
        df = self.clean if self.clean is not None else self.clean_data()
        trend = (
            df.set_index("incident_date")
              .resample("ME")
              .size()
              .rename("incidents")
              .reset_index()
        )
        # Simple 3-month moving average as a lightweight forecast baseline
        trend["moving_avg_3m"] = trend["incidents"].rolling(3, min_periods=1).mean().round(1)
        return trend

    def severity_by_site(self) -> pd.DataFrame:
        df = self.clean if self.clean is not None else self.clean_data()
        return (
            df.groupby(["site_name", "severity"])
              .size()
              .rename("count")
              .reset_index()
        )

    def root_cause_pareto(self) -> pd.DataFrame:
        df = self.clean if self.clean is not None else self.clean_data()
        pareto = df["root_cause"].value_counts().reset_index()
        pareto.columns = ["root_cause", "count"]
        pareto["cumulative_pct"] = (
            100 * pareto["count"].cumsum() / pareto["count"].sum()
        ).round(1)
        return pareto


def run_pipeline(csv_path: str | Path) -> tuple[pd.DataFrame, QualityReport]:
    """Convenience entry point: profile + clean in one call."""
    proc = IncidentDataProcessor(csv_path)
    proc.load()
    report = proc.profile()
    clean = proc.clean_data()
    return clean, report


if __name__ == "__main__":
    base = Path(__file__).resolve().parents[1]
    clean_df, rep = run_pipeline(base / "data" / "raw_incidents.csv")
    print(rep.summary().to_string(index=False))
    print(f"\nClean records: {len(clean_df)}")
