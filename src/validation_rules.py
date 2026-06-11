"""
Regulatory Compliance Validation Rules
=======================================
Automated validation rules inspired by HSE regulatory frameworks
(OSHA recordkeeping, Argentine SRT Res. 81/2019, ISO 45001 clauses).

Each rule returns a ValidationResult with pass/fail status and the
offending records, enabling auditable compliance reporting.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

VALID_SEVERITIES = ["Near Miss", "First Aid", "Medical Treatment",
                    "Lost Time Injury", "Fatality"]


@dataclass
class ValidationResult:
    rule_id: str
    description: str
    passed: bool
    violations: int
    violation_indices: list
    severity: str  # "critical" | "warning" | "info"

    def as_dict(self) -> dict:
        return {
            "rule_id": self.rule_id,
            "description": self.description,
            "status": "PASS" if self.passed else "FAIL",
            "violations": self.violations,
            "severity": self.severity,
        }


class ComplianceValidator:
    """Runs a battery of regulatory-style validation rules over incident data."""

    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()
        if not pd.api.types.is_datetime64_any_dtype(self.df["incident_date"]):
            self.df["incident_date"] = pd.to_datetime(
                self.df["incident_date"], errors="coerce"
            )

    # ------------------------------------------------------------ rule defs
    def rule_unique_incident_ids(self) -> ValidationResult:
        dup_mask = self.df.duplicated(subset=["incident_id"], keep=False)
        idx = self.df[dup_mask].index.tolist()
        return ValidationResult(
            "R001", "Incident IDs must be unique",
            len(idx) == 0, len(idx), idx, "critical",
        )

    def rule_no_future_dates(self) -> ValidationResult:
        today = pd.Timestamp.today().normalize()
        mask = self.df["incident_date"].isna() | (self.df["incident_date"] > today)
        idx = self.df[mask].index.tolist()
        return ValidationResult(
            "R002", "Incident dates must be valid and not in the future",
            len(idx) == 0, len(idx), idx, "critical",
        )

    def rule_valid_severity(self) -> ValidationResult:
        mask = ~self.df["severity"].isin(VALID_SEVERITIES)
        idx = self.df[mask].index.tolist()
        return ValidationResult(
            "R003", "Severity must use the standard 5-level classification",
            len(idx) == 0, len(idx), idx, "critical",
        )

    def rule_fatalities_require_action(self) -> ValidationResult:
        fatal = self.df[self.df["severity"] == "Fatality"]
        mask = fatal["corrective_action"].isna() | (
            fatal["corrective_action"] == "Pending investigation"
        )
        idx = fatal[mask].index.tolist()
        return ValidationResult(
            "R004", "Fatalities must have a documented corrective action",
            len(idx) == 0, len(idx), idx, "warning",
        )

    def rule_lti_requires_days_lost(self) -> ValidationResult:
        lti = self.df[self.df["severity"] == "Lost Time Injury"]
        mask = lti["days_lost"].fillna(0) < 1
        idx = lti[mask].index.tolist()
        return ValidationResult(
            "R005", "Lost Time Injuries must record at least 1 day lost",
            len(idx) == 0, len(idx), idx, "warning",
        )

    def rule_worker_age_legal(self) -> ValidationResult:
        ages = pd.to_numeric(self.df["worker_age"], errors="coerce")
        mask = ages.notna() & ~ages.between(18, 70)
        idx = self.df[mask].index.tolist()
        return ValidationResult(
            "R006", "Worker age must be within legal employment range (18-70)",
            len(idx) == 0, len(idx), idx, "critical",
        )

    def rule_no_negative_days_lost(self) -> ValidationResult:
        days = pd.to_numeric(self.df["days_lost"], errors="coerce")
        mask = days < 0
        idx = self.df[mask].index.tolist()
        return ValidationResult(
            "R007", "Days lost cannot be negative",
            len(idx) == 0, len(idx), idx, "critical",
        )

    def rule_24h_reporting_rate(self, min_rate: float = 0.85) -> ValidationResult:
        rate = self.df["reported_within_24h"].mean()
        passed = bool(rate >= min_rate)
        late_idx = self.df[~self.df["reported_within_24h"].astype(bool)].index.tolist()
        return ValidationResult(
            "R008",
            f"At least {min_rate:.0%} of incidents reported within 24h "
            f"(actual: {rate:.1%})",
            passed, 0 if passed else len(late_idx), late_idx, "warning",
        )

    def rule_root_cause_documented(self) -> ValidationResult:
        serious = self.df[self.df["severity"].isin(
            ["Medical Treatment", "Lost Time Injury", "Fatality"])]
        mask = serious["root_cause"].isna()
        idx = serious[mask].index.tolist()
        return ValidationResult(
            "R009", "Serious incidents must have a documented root cause",
            len(idx) == 0, len(idx), idx, "warning",
        )

    def rule_location_coordinates_valid(self) -> ValidationResult:
        lat_ok = self.df["latitude"].between(-90, 90)
        lon_ok = self.df["longitude"].between(-180, 180)
        mask = ~(lat_ok & lon_ok)
        idx = self.df[mask].index.tolist()
        return ValidationResult(
            "R010", "Geographic coordinates must be valid lat/lon pairs",
            len(idx) == 0, len(idx), idx, "info",
        )

    # ------------------------------------------------------------- run all
    def run_all(self) -> pd.DataFrame:
        rules = [
            self.rule_unique_incident_ids(),
            self.rule_no_future_dates(),
            self.rule_valid_severity(),
            self.rule_fatalities_require_action(),
            self.rule_lti_requires_days_lost(),
            self.rule_worker_age_legal(),
            self.rule_no_negative_days_lost(),
            self.rule_24h_reporting_rate(),
            self.rule_root_cause_documented(),
            self.rule_location_coordinates_valid(),
        ]
        self.results = rules
        return pd.DataFrame([r.as_dict() for r in rules])

    def compliance_rate(self) -> float:
        if not hasattr(self, "results"):
            self.run_all()
        passed = sum(1 for r in self.results if r.passed)
        return round(100 * passed / len(self.results), 1)


if __name__ == "__main__":
    from pathlib import Path
    from data_processor import run_pipeline

    base = Path(__file__).resolve().parents[1]
    clean_df, _ = run_pipeline(base / "data" / "raw_incidents.csv")
    validator = ComplianceValidator(clean_df)
    print(validator.run_all().to_string(index=False))
    print(f"\nCompliance rate: {validator.compliance_rate()}%")
