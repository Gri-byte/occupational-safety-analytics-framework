# Architecture

## Overview

The framework follows a simple, testable three-layer design: **Data → Processing → Presentation**. Every layer is independently runnable and covered by automated tests.

```
┌─────────────────────────────────────────────────────────────┐
│                       DATA LAYER                            │
│  generate_data.py ──▶ data/raw_incidents.csv                │
│  • 530 synthetic records, seed=42 (fully reproducible)      │
│  • Quality issues embedded intentionally:                   │
│    duplicates, NaNs, outliers, invalid dates, bad labels    │
└──────────────────────────┬──────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    PROCESSING LAYER                         │
│                                                             │
│  IncidentDataProcessor (data_processor.py)                  │
│  ├── load()         CSV ingestion                           │
│  ├── profile()      QualityReport: dupes, NaNs, outliers,   │
│  │                  invalid dates/labels, quality score     │
│  ├── detect_outliers_iqr()  / detect_outliers_zscore()      │
│  ├── clean_data()   rule-based, auditable transformations   │
│  └── kpis() / monthly_trend() / root_cause_pareto()         │
│                                                             │
│  ComplianceValidator (validation_rules.py)                  │
│  └── 10 rules (R001–R010) → ValidationResult objects        │
│      each with status, violation count, and indices         │
└──────────────────────────┬──────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  PRESENTATION LAYER                         │
│  dashboard.py (Streamlit + Plotly)                          │
│  • Sidebar filters: industry, site, severity, date range    │
│  • Tabs: Trends | Breakdown | Map | Data Quality | Report   │
│  • Exports: executive summary (MD), cleaned dataset (CSV)   │
└─────────────────────────────────────────────────────────────┘
```

## Design Decisions

### Why synthetic data with embedded issues?
Real HSE data is confidential. Generating it synthetically (with a fixed seed) makes the project fully reproducible while still exercising realistic failure modes: duplicate reports filed by two supervisors, severity recorded as "MTC" instead of "Medical Treatment", a typo producing a future date, etc.

### Why dataclasses for reports and results?
`QualityReport` and `ValidationResult` give structured, serializable outputs that are easy to test, log, or push to a downstream system (e.g., a BI tool or alerting pipeline) — instead of opaque print statements.

### Outlier detection: IQR vs Z-score
Both are implemented as static methods so they can be unit-tested in isolation:

- **IQR (k=1.5)**: robust to skewed distributions — appropriate for `days_lost`, which follows a heavy right tail.
- **Z-score (threshold=3)**: classic parametric approach; handles the degenerate constant-series case explicitly.

The profiling step runs both and reports them separately, letting an analyst compare sensitivity.

### Cleaning philosophy: conservative and auditable
Cleaning never invents data. Records with unfixable integrity problems (future dates, illegal ages) are **dropped**; recoverable issues are **normalized** (severity label mapping) or **flagged** (missing root cause → "Under investigation"). The test suite asserts that ≥ 90% of records survive cleaning, guarding against over-aggressive filters.

### Compliance rules as first-class objects
Each rule is an isolated method returning a `ValidationResult`, mirroring how rules engines work in production data quality tools (Great Expectations, dbt tests, Soda). New rules are added by writing one method and appending it to `run_all()`.

## Extensibility Roadmap

| Extension | How |
|---|---|
| PostgreSQL backend | Replace `pd.read_csv` with SQLAlchemy in `load()` |
| Real forecasting | Swap moving average for `statsmodels` SARIMA in `monthly_trend()` |
| PDF reports | Render the executive summary with `reportlab` or `weasyprint` |
| Scheduled audits | Wrap `run_pipeline()` in a GitHub Actions cron workflow |
| Great Expectations | Map R001–R010 to GE expectation suites |
