"""
Centralised configuration for the HSE Analytics Framework.

All tuneable constants live here so the rest of the codebase never
needs hard-coded paths or magic numbers.
"""

from __future__ import annotations

from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ROOT_DIR: Path = Path(__file__).resolve().parents[3]
DATA_DIR: Path = ROOT_DIR / "data"
LOGS_DIR: Path = ROOT_DIR / "logs"

RAW_DATA_PATH: Path = DATA_DIR / "raw_incidents.csv"
LOG_FILE: Path = LOGS_DIR / "hse_pipeline.log"

# ---------------------------------------------------------------------------
# Outlier detection thresholds
# ---------------------------------------------------------------------------

IQR_K: float = 1.5          # Tukey fence multiplier
ZSCORE_THRESHOLD: float = 3.0

# ---------------------------------------------------------------------------
# Compliance thresholds
# ---------------------------------------------------------------------------

MIN_REPORTING_RATE_24H: float = 0.85   # Rule R008
MIN_WORKER_AGE: int = 18
MAX_WORKER_AGE: int = 70

# ---------------------------------------------------------------------------
# Dashboard defaults
# ---------------------------------------------------------------------------

DASHBOARD_TITLE: str = "HSE Analytics | Mining & Petroleum"
DASHBOARD_ICON: str = "⛑️"
MAP_CENTER: dict = {"lat": -40, "lon": -68}
MAP_ZOOM: float = 3.2

# ---------------------------------------------------------------------------
# Data generation
# ---------------------------------------------------------------------------

GENERATE_SEED: int = 42
GENERATE_N_RECORDS: int = 520