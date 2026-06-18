"""
Shared pytest fixtures for the HSE Analytics test suite.
"""

import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

DATA_PATH = ROOT / "data" / "raw_incidents.csv"


@pytest.fixture(scope="session")
def raw_data_path() -> Path:
    return DATA_PATH


@pytest.fixture(scope="session")
def minimal_clean_df() -> pd.DataFrame:
    """A tiny but structurally valid clean DataFrame for unit tests."""
    return pd.DataFrame(
        {
            "incident_id": [f"INC-2024-{i:04d}" for i in range(1, 11)],
            "incident_date": pd.date_range("2024-01-01", periods=10, freq="ME"),
            "site_name": ["Site A"] * 5 + ["Site B"] * 5,
            "industry": ["mining"] * 5 + ["petroleum"] * 5,
            "severity": [
                "Near Miss", "First Aid", "Medical Treatment",
                "Lost Time Injury", "Fatality",
                "Near Miss", "First Aid", "Medical Treatment",
                "Lost Time Injury", "Near Miss",
            ],
            "incident_type": ["Slip/Trip/Fall"] * 10,
            "root_cause": ["Equipment failure"] * 10,
            "equipment_involved": ["Crane"] * 10,
            "worker_age": [30, 35, 40, 45, 50, 32, 38, 42, 28, 55],
            "worker_tenure_years": [2.0, 5.0, 8.0, 3.0, 10.0, 1.0, 4.0, 6.0, 2.5, 12.0],
            "days_lost": [0, 0, 3, 10, 0, 0, 0, 5, 7, 0],
            "corrective_action": ["Refresher training delivered"] * 10,
            "reported_within_24h": [True] * 9 + [False],
            "latitude": [-38.45] * 10,
            "longitude": [-68.85] * 10,
            "province": ["Neuquen"] * 10,
            "country": ["AR"] * 10,
            "worker_gender": ["M"] * 8 + ["F"] * 2,
            "shift": ["Day"] * 10,
        }
    )


@pytest.fixture(scope="session")
def empty_df(minimal_clean_df) -> pd.DataFrame:
    """An empty DataFrame with the same schema."""
    return minimal_clean_df.iloc[0:0].copy()