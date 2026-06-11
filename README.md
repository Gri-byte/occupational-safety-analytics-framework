# ⛑️ Occupational Safety Analytics Framework

**Production-ready HSE (Health, Safety & Environment) data analytics for mining and petroleum operations** — data quality auditing, anomaly detection, regulatory compliance validation, and an interactive Streamlit dashboard.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Pandas](https://img.shields.io/badge/Pandas-2.x-150458)
![Streamlit](https://img.shields.io/badge/Streamlit-Dashboard-FF4B4B)
![Tests](https://img.shields.io/badge/Tests-27%20passing-success)
![License](https://img.shields.io/badge/License-MIT-green)

## 🎯 Why This Project

High-risk industries (mining, oil & gas) depend on trustworthy incident data to prevent fatalities and pass regulatory audits. Yet HSE datasets are notoriously messy: duplicated reports, missing root causes, impossible dates, inconsistent severity labels.

This framework demonstrates the full lifecycle of an HSE data product:

1. **Profile** raw incident data and quantify its quality (score 0–100)
2. **Detect anomalies** with statistical methods (IQR, Z-score)
3. **Validate** against 10 regulatory-style compliance rules (OSHA / SRT / ISO 45001 inspired)
4. **Clean** the data with auditable, rule-based transformations
5. **Visualize** KPIs, trends, Pareto root-cause analysis, and geographic incident density

> Built with a QA engineering mindset: every transformation is covered by automated tests (27 pytest cases).

## 📸 Dashboard Preview

The Streamlit dashboard includes:

- **KPI cards**: total incidents, LTIs, fatalities, avg days lost, 24h reporting rate
- **Trends tab**: monthly incident series with 3-month moving-average forecast baseline
- **Breakdown tab**: severity donut, top hazards, root-cause Pareto chart
- **Map tab**: geographic incident density across Argentine mining/petroleum sites
- **Data Quality tab**: quality score, profiling summary, live compliance check results
- **Report tab**: downloadable executive summary (Markdown) and cleaned dataset (CSV)

## 🏗️ Architecture

```
raw_incidents.csv ──▶ IncidentDataProcessor ──▶ clean DataFrame ──▶ Dashboard
                          │                            │
                          ▼                            ▼
                    QualityReport              ComplianceValidator
                  (profiling, outliers)        (10 regulatory rules)
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full design.

## 🚀 Quick Start

```bash
# 1. Clone and set up environment
git clone https://github.com/Gri-byte/occupational-safety-analytics-framework.git
cd occupational-safety-analytics-framework
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/Mac
pip install -r requirements.txt

# 2. Generate the synthetic dataset
python src/generate_data.py

# 3. Run the quality pipeline (CLI summary)
python src/data_processor.py
python src/validation_rules.py

# 4. Run the test suite
pytest tests/ -v

# 5. Launch the dashboard
streamlit run src/dashboard.py
```

## 📁 Project Structure

```
occupational-safety-analytics-framework/
├── data/
│   └── raw_incidents.csv          # Synthetic dataset (530 records, issues embedded)
├── src/
│   ├── generate_data.py           # Reproducible synthetic data generator (seed=42)
│   ├── data_processor.py          # Profiling, IQR/Z-score outliers, cleaning, KPIs
│   ├── validation_rules.py        # 10 regulatory compliance rules
│   └── dashboard.py               # Streamlit interactive dashboard
├── tests/
│   └── test_data_quality.py       # 27 pytest cases
├── docs/
│   ├── ARCHITECTURE.md
│   ├── DATA_DICTIONARY.md
│   └── BUSINESS_CASE.md
├── requirements.txt
├── .gitignore
└── README.md
```

## ✅ Compliance Rules Implemented

| Rule | Description | Severity |
|------|-------------|----------|
| R001 | Incident IDs must be unique | Critical |
| R002 | No future/invalid incident dates | Critical |
| R003 | Standard 5-level severity classification | Critical |
| R004 | Fatalities require documented corrective action | Warning |
| R005 | LTIs must record ≥ 1 day lost | Warning |
| R006 | Worker age within legal range (18–70) | Critical |
| R007 | Days lost cannot be negative | Critical |
| R008 | ≥ 85% of incidents reported within 24h | Warning |
| R009 | Serious incidents need documented root cause | Warning |
| R010 | Valid geographic coordinates | Info |

## 🧪 Skills Demonstrated

- **Data Quality Engineering**: profiling, scoring, auditable cleaning rules
- **Statistical Anomaly Detection**: IQR and Z-score methods with unit tests
- **Regulatory Domain Knowledge**: OSHA recordkeeping, ISO 45001, Argentine SRT concepts
- **Dashboard Development**: Streamlit + Plotly with filters, maps, and exports
- **Test Automation**: pytest fixtures, parametrized validation, 100% rule coverage

## 📄 License

MIT — free to use as a reference for HSE analytics implementations.

---

**Author:** Fabiana Grisel González ([@Gri-byte](https://github.com/Gri-byte)) — QA Automation Engineer transitioning into Data Engineering, specialized in data quality for high-risk industries.
