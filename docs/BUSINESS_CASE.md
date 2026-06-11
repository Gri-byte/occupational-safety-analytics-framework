# Business Case: HSE Data Analytics for Mining & Petroleum

## The Problem

Mining and oil & gas remain among the most hazardous industries worldwide. Beyond the human cost, every Lost Time Injury carries direct costs (medical, compensation, downtime) and indirect costs (investigation, retraining, equipment, reputation) that industry studies typically estimate at **4–10× the direct cost**.

In Argentina specifically, operators in Vaca Muerta, the Santa Cruz gold/silver district, and the San Juan cordillera report to the SRT (Superintendencia de Riesgos del Trabajo) and face increasingly strict ESG scrutiny from international investors and ISO 45001 certification audits.

**The hidden problem: the data itself.** Safety decisions are only as good as the incident data behind them. In practice, HSE registries suffer from:

- **Duplicate reports** — the same incident filed by a field supervisor and a safety officer
- **Missing root causes** — investigations never closed, breaking Pareto analysis
- **Label inconsistency** — "MTC", "Medical Treatment", "MEDICAL TREATMENT" counted as three categories, distorting severity pyramids
- **Impossible values** — negative days lost, workers aged 102, incidents dated in the future
- **Late reporting** — regulatory exposure when 24h notification thresholds are missed

A safety dashboard built on dirty data produces **confidently wrong conclusions**: underestimated LTIFR, misranked hazards, missed site-level deterioration trends.

## The Solution

This framework treats HSE data with the same rigor as financial data:

1. **Quantified quality** — every dataset gets a 0–100 quality score before anyone makes decisions on it
2. **Statistical anomaly detection** — IQR and Z-score flag suspicious `days_lost` and demographic values for human review
3. **Codified compliance** — 10 automated rules encode regulatory expectations (unique IDs, valid dates, documented corrective actions for fatalities, 24h reporting rate ≥ 85%)
4. **Auditable cleaning** — every transformation is rule-based, tested, and explainable to an auditor
5. **Decision-ready visualization** — KPIs, trend forecasting baseline, root-cause Pareto, and geographic density in one dashboard

## Quantified Value Scenarios

| Stakeholder | Pain | Value Delivered |
|---|---|---|
| HSE Manager | Monthly reports take days of manual Excel cleanup | Automated pipeline: raw CSV → clean dashboard in seconds |
| Compliance Officer | Audit findings on incomplete fatality records | Rule R004 flags undocumented corrective actions continuously |
| Site Superintendent | Doesn't know which hazard to attack first | Pareto analysis identifies the ~20% of root causes driving ~80% of incidents |
| Executive / ESG | Investor questionnaires need defensible LTIFR | KPIs computed from validated data with a documented methodology |

## Why a QA Engineer Builds This Better

Data quality in safety-critical contexts **is** a testing problem:

- Validation rules are assertions; compliance checks are test suites
- Edge cases (constant series in Z-score, empty severity sets) are caught by design
- The 27-test pytest suite means the pipeline itself is regression-protected — a property most analytics scripts lack

This project applies 3+ years of QA automation discipline (Playwright, CI/CD, Oracle SQL validation) to the data engineering domain, targeting industries where bad data costs lives, not just money.

## Deployment Path (Production Roadmap)

1. **Pilot**: connect to the operator's incident registry (PostgreSQL / SAP EHS export)
2. **Automate**: nightly pipeline run via GitHub Actions or Airflow, quality score alerting below threshold
3. **Integrate**: push validated KPIs to Power BI / Looker; expose compliance results to audit teams
4. **Extend**: SARIMA forecasting, leading-indicator analysis (near-miss ratios), NLP on incident descriptions
