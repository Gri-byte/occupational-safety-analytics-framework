"""
Synthetic HSE Incident Data Generator
======================================
Generates realistic occupational safety incident records for mining and
petroleum operations, with intentionally embedded data quality issues
(duplicates, missing values, outliers, inconsistent formats) to showcase
the validation and cleaning pipeline.

Usage:
    python src/generate_data.py
Output:
    data/raw_incidents.csv
"""

import random
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 42
N_RECORDS = 520

random.seed(SEED)
np.random.seed(SEED)

# ---------------------------------------------------------------------------
# Reference catalogs (domain-realistic for mining & petroleum in LATAM)
# ---------------------------------------------------------------------------

SITES = [
    ("Cerro Negro Mine", "Santa Cruz", "AR", -46.95, -70.05, "mining"),
    ("Vaca Muerta Field", "Neuquen", "AR", -38.45, -68.85, "petroleum"),
    ("Cerro Vanguardia", "Santa Cruz", "AR", -48.35, -68.30, "mining"),
    ("Golfo San Jorge Basin", "Chubut", "AR", -45.85, -67.50, "petroleum"),
    ("Veladero Mine", "San Juan", "AR", -29.35, -69.95, "mining"),
    ("Loma Campana", "Neuquen", "AR", -38.65, -68.55, "petroleum"),
    ("Lindero Mine", "Salta", "AR", -24.85, -67.55, "mining"),
    ("Manantiales Behr", "Chubut", "AR", -45.55, -67.65, "petroleum"),
]

INCIDENT_TYPES = {
    "Slip/Trip/Fall": 0.18,
    "Struck by Object": 0.14,
    "Caught in Equipment": 0.10,
    "Vehicle Collision": 0.12,
    "Chemical Exposure": 0.09,
    "Gas Leak": 0.07,
    "Electrical Contact": 0.06,
    "Fire/Explosion": 0.04,
    "Falling from Height": 0.08,
    "Rockfall/Ground Failure": 0.07,
    "Heat Stress": 0.05,
}

ROOT_CAUSES = [
    "Inadequate training",
    "PPE not used or defective",
    "Procedure not followed",
    "Equipment failure",
    "Poor housekeeping",
    "Inadequate risk assessment",
    "Fatigue / human error",
    "Insufficient supervision",
    "Environmental conditions",
    "Communication failure",
]

EQUIPMENT = [
    "Haul truck", "Drill rig", "Excavator", "Conveyor belt", "Crane",
    "Wellhead assembly", "Pump unit", "Compressor", "Light vehicle",
    "Hand tools", "Scaffolding", "None",
]

CORRECTIVE_ACTIONS = [
    "Refresher training delivered",
    "PPE replaced and inspection scheduled",
    "Procedure revised and communicated",
    "Equipment repaired and recertified",
    "Area housekeeping audit implemented",
    "Job hazard analysis updated",
    "Shift rotation adjusted",
    "Supervision checklist introduced",
    "Engineering control installed",
    "Pending investigation",
]

SEVERITY_LEVELS = ["Near Miss", "First Aid", "Medical Treatment",
                   "Lost Time Injury", "Fatality"]
SEVERITY_WEIGHTS = [0.38, 0.27, 0.20, 0.13, 0.02]

SHIFTS = ["Day", "Night", "Rotating"]
GENDERS = ["M", "F"]


def _random_date(start: datetime, end: datetime) -> datetime:
    delta = end - start
    return start + timedelta(days=random.randint(0, delta.days),
                             hours=random.randint(0, 23),
                             minutes=random.choice([0, 15, 30, 45]))


def generate_clean_records(n: int) -> pd.DataFrame:
    start = datetime(2023, 1, 1)
    end = datetime(2025, 12, 31)
    rows = []
    types, type_probs = zip(*INCIDENT_TYPES.items())

    for i in range(n):
        site = random.choice(SITES)
        severity = random.choices(SEVERITY_LEVELS, weights=SEVERITY_WEIGHTS)[0]
        incident_date = _random_date(start, end)

        # Days lost correlates with severity
        days_lost = {
            "Near Miss": 0,
            "First Aid": 0,
            "Medical Treatment": int(np.random.gamma(2, 1.5)),
            "Lost Time Injury": int(np.random.gamma(4, 5)) + 1,
            "Fatality": 0,
        }[severity]

        rows.append({
            "incident_id": f"INC-{2023 + incident_date.year - 2023}-{i + 1:04d}",
            "incident_date": incident_date.strftime("%Y-%m-%d"),
            "incident_time": incident_date.strftime("%H:%M"),
            "site_name": site[0],
            "province": site[1],
            "country": site[2],
            "latitude": site[3] + np.random.normal(0, 0.05),
            "longitude": site[4] + np.random.normal(0, 0.05),
            "industry": site[5],
            "incident_type": random.choices(types, weights=type_probs)[0],
            "severity": severity,
            "root_cause": random.choice(ROOT_CAUSES),
            "equipment_involved": random.choice(EQUIPMENT),
            "worker_age": int(np.clip(np.random.normal(38, 9), 18, 65)),
            "worker_gender": random.choices(GENDERS, weights=[0.85, 0.15])[0],
            "worker_tenure_years": round(float(np.clip(np.random.exponential(5), 0.1, 35)), 1),
            "shift": random.choice(SHIFTS),
            "days_lost": days_lost,
            "corrective_action": random.choice(CORRECTIVE_ACTIONS),
            "reported_within_24h": random.choices([True, False], weights=[0.9, 0.1])[0],
        })
    return pd.DataFrame(rows)


def inject_quality_issues(df: pd.DataFrame) -> pd.DataFrame:
    """Embed realistic data quality problems for the pipeline to detect."""
    df = df.copy()

    # 1. Exact duplicates (~2%)
    dupes = df.sample(10, random_state=SEED)
    df = pd.concat([df, dupes], ignore_index=True)

    # 2. Missing values
    for col, frac in [("root_cause", 0.05), ("corrective_action", 0.04),
                      ("worker_age", 0.03), ("equipment_involved", 0.03)]:
        idx = df.sample(frac=frac, random_state=SEED).index
        df.loc[idx, col] = np.nan

    # 3. Numeric outliers
    out_idx = df.sample(6, random_state=SEED + 1).index
    df.loc[out_idx, "days_lost"] = np.random.randint(180, 400, size=len(out_idx))
    age_idx = df.sample(4, random_state=SEED + 2).index
    df.loc[age_idx, "worker_age"] = [15, 17, 88, 102]  # invalid ages

    # 4. Inconsistent severity casing/labels
    sev_idx = df.sample(12, random_state=SEED + 3).index
    df.loc[sev_idx, "severity"] = df.loc[sev_idx, "severity"].str.upper()
    mt_idx = df[df["severity"] == "Medical Treatment"].sample(5, random_state=SEED + 4).index
    df.loc[mt_idx, "severity"] = "MTC"  # non-standard abbreviation

    # 5. Future dates (impossible)
    fut_idx = df.sample(3, random_state=SEED + 5).index
    df.loc[fut_idx, "incident_date"] = "2027-06-15"

    # 6. Negative days_lost
    neg_idx = df.sample(3, random_state=SEED + 6).index
    df.loc[neg_idx, "days_lost"] = -2

    return df.sample(frac=1, random_state=SEED).reset_index(drop=True)


def main() -> None:
    out_path = Path(__file__).resolve().parents[1] / "data" / "raw_incidents.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    df = generate_clean_records(N_RECORDS)
    df = inject_quality_issues(df)
    df.to_csv(out_path, index=False)
    print(f"Generated {len(df)} records -> {out_path}")


if __name__ == "__main__":
    main()
