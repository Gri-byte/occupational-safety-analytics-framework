# Data Dictionary

Dataset: `data/raw_incidents.csv` — synthetic HSE incident records for mining and petroleum operations in Argentina (2023–2025).

| Field | Type | Description | Valid Values / Range | Notes |
|---|---|---|---|---|
| `incident_id` | string | Unique incident identifier | `INC-YYYY-NNNN` | Primary key; raw data contains duplicates by design |
| `incident_date` | date | Date the incident occurred | 2023-01-01 → today | Raw data contains future dates (invalid) |
| `incident_time` | string | Time of occurrence | `HH:MM` 24h | Quarter-hour granularity |
| `site_name` | string | Operating site | 8 sites (4 mining, 4 petroleum) | e.g., "Cerro Negro Mine", "Vaca Muerta Field" |
| `province` | string | Argentine province | Santa Cruz, Neuquén, Chubut, San Juan, Salta | |
| `country` | string | ISO country code | `AR` | |
| `latitude` | float | Site latitude with jitter | −90 → 90 | Jitter ±0.05° simulates within-site locations |
| `longitude` | float | Site longitude with jitter | −180 → 180 | |
| `industry` | string | Industry segment | `mining`, `petroleum` | |
| `incident_type` | string | Hazard classification | 11 categories | Slip/Trip/Fall, Gas Leak, Rockfall, etc. |
| `severity` | string | Outcome severity | Near Miss, First Aid, Medical Treatment, Lost Time Injury, Fatality | Raw data contains uppercase variants and "MTC" abbreviation |
| `root_cause` | string | Investigated root cause | 10 categories | ~5% missing in raw data |
| `equipment_involved` | string | Equipment in incident | 12 categories incl. "None" | ~3% missing in raw data |
| `worker_age` | int | Age of affected worker | 18–65 (valid) | Raw data contains illegal values (15, 102) |
| `worker_gender` | string | Gender | `M`, `F` | 85/15 distribution reflects industry demographics |
| `worker_tenure_years` | float | Years at the company | 0.1–35 | Exponential distribution (many junior workers) |
| `shift` | string | Work shift | Day, Night, Rotating | |
| `days_lost` | int | Work days lost | ≥ 0 | Correlated with severity; raw data has negatives and extreme outliers |
| `corrective_action` | string | Action taken | 10 categories | ~4% missing in raw data |
| `reported_within_24h` | bool | Regulatory reporting compliance | True/False | ~90% True |

## Severity Classification Reference

Standard 5-level scale used across the framework (consistent with common HSE pyramids):

1. **Near Miss** — no injury, potential identified
2. **First Aid** — minor injury, on-site treatment only
3. **Medical Treatment** — professional medical care, no lost time (a.k.a. MTC)
4. **Lost Time Injury (LTI)** — at least one full day/shift lost
5. **Fatality** — work-related death

## KPI Definitions

| KPI | Formula | Standard |
|---|---|---|
| LTIFR | (LTIs × 1,000,000) / hours worked | Per million hours (international convention) |
| Avg Days Lost | mean(`days_lost`) over all incidents | Severity proxy |
| 24h Reporting Rate | % incidents with `reported_within_24h = True` | Threshold: ≥ 85% (rule R008) |
