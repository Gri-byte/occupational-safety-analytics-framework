"""
HSE Analytics Dashboard (Streamlit)
====================================
Interactive dashboard for occupational safety metrics in mining and
petroleum operations.

Run with:
    streamlit run src/dashboard.py
"""

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from data_processor import IncidentDataProcessor
from validation_rules import ComplianceValidator

BASE = Path(__file__).resolve().parents[1]
DATA_PATH = BASE / "data" / "raw_incidents.csv"

st.set_page_config(
    page_title="HSE Analytics | Mining & Petroleum",
    page_icon="⛑️",
    layout="wide",
)


# ---------------------------------------------------------------- data load
@st.cache_data
def load_data():
    proc = IncidentDataProcessor(DATA_PATH)
    proc.load()
    report = proc.profile()
    clean = proc.clean_data()
    return proc, clean, report


proc, df, quality_report = load_data()

# ---------------------------------------------------------------- sidebar
st.sidebar.title("⛑️ HSE Analytics")
st.sidebar.markdown("Occupational Safety Framework\nfor Mining & Petroleum")

industries = st.sidebar.multiselect(
    "Industry", sorted(df["industry"].unique()),
    default=sorted(df["industry"].unique()),
)
sites = st.sidebar.multiselect(
    "Site", sorted(df["site_name"].unique()),
    default=sorted(df["site_name"].unique()),
)
severities = st.sidebar.multiselect(
    "Severity", sorted(df["severity"].unique()),
    default=sorted(df["severity"].unique()),
)
date_range = st.sidebar.date_input(
    "Date range",
    value=(df["incident_date"].min().date(), df["incident_date"].max().date()),
)

mask = (
    df["industry"].isin(industries)
    & df["site_name"].isin(sites)
    & df["severity"].isin(severities)
)
if isinstance(date_range, tuple) and len(date_range) == 2:
    mask &= df["incident_date"].between(
        pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1])
    )
fdf = df[mask]

st.title("Occupational Safety Analytics Dashboard")
st.caption(f"Showing {len(fdf):,} of {len(df):,} cleaned incident records")

# ---------------------------------------------------------------- KPI cards
total = len(fdf)
lti = int((fdf["severity"] == "Lost Time Injury").sum())
fatalities = int((fdf["severity"] == "Fatality").sum())
avg_days = fdf["days_lost"].mean() if total else 0
pct_24h = 100 * fdf["reported_within_24h"].mean() if total else 0

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Total Incidents", f"{total:,}")
c2.metric("Lost Time Injuries", lti)
c3.metric("Fatalities", fatalities, delta_color="inverse")
c4.metric("Avg Days Lost", f"{avg_days:.1f}")
c5.metric("Reported < 24h", f"{pct_24h:.0f}%")

st.divider()

# ---------------------------------------------------------------- tabs
tab_trend, tab_breakdown, tab_map, tab_quality, tab_report = st.tabs(
    ["📈 Trends", "📊 Breakdown", "🗺️ Map", "✅ Data Quality", "📄 Report"]
)

with tab_trend:
    trend = (
        fdf.set_index("incident_date").resample("ME").size()
           .rename("incidents").reset_index()
    )
    trend["moving_avg_3m"] = trend["incidents"].rolling(3, min_periods=1).mean()

    fig = go.Figure()
    fig.add_trace(go.Bar(x=trend["incident_date"], y=trend["incidents"],
                         name="Incidents", marker_color="#4C78A8"))
    fig.add_trace(go.Scatter(x=trend["incident_date"], y=trend["moving_avg_3m"],
                             name="3-month moving avg", mode="lines",
                             line=dict(color="#E45756", width=3)))
    fig.update_layout(title="Monthly Incident Trend", height=420,
                      legend=dict(orientation="h", y=1.1))
    st.plotly_chart(fig, use_container_width=True)

    # naive forecast: extend moving average 3 months ahead
    if len(trend) >= 3:
        last_avg = trend["moving_avg_3m"].iloc[-1]
        st.info(f"📌 Baseline forecast (3-month moving average): "
                f"~{last_avg:.0f} incidents/month expected for the next quarter.")

with tab_breakdown:
    col_a, col_b = st.columns(2)
    with col_a:
        sev_counts = fdf["severity"].value_counts().reset_index()
        sev_counts.columns = ["severity", "count"]
        fig = px.pie(sev_counts, names="severity", values="count",
                     title="Severity Distribution", hole=0.45)
        st.plotly_chart(fig, use_container_width=True)
    with col_b:
        type_counts = fdf["incident_type"].value_counts().head(8).reset_index()
        type_counts.columns = ["incident_type", "count"]
        fig = px.bar(type_counts, x="count", y="incident_type",
                     orientation="h", title="Top Hazards (Incident Types)")
        fig.update_layout(yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig, use_container_width=True)

    pareto = fdf["root_cause"].value_counts().reset_index()
    pareto.columns = ["root_cause", "count"]
    pareto["cumulative_pct"] = 100 * pareto["count"].cumsum() / pareto["count"].sum()
    fig = go.Figure()
    fig.add_trace(go.Bar(x=pareto["root_cause"], y=pareto["count"], name="Count"))
    fig.add_trace(go.Scatter(x=pareto["root_cause"], y=pareto["cumulative_pct"],
                             name="Cumulative %", yaxis="y2",
                             line=dict(color="#E45756")))
    fig.update_layout(
        title="Root Cause Pareto Analysis",
        yaxis2=dict(overlaying="y", side="right", range=[0, 105], ticksuffix="%"),
        height=420,
    )
    st.plotly_chart(fig, use_container_width=True)

with tab_map:
    site_agg = (
        fdf.groupby(["site_name", "industry"])
           .agg(incidents=("incident_id", "count"),
                latitude=("latitude", "mean"),
                longitude=("longitude", "mean"))
           .reset_index()
    )
    fig = px.scatter_map(
        site_agg, lat="latitude", lon="longitude",
        size="incidents", color="industry",
        hover_name="site_name", zoom=3.2,
        title="Incident Density by Site",
        center={"lat": -40, "lon": -68},
    )
    fig.update_layout(height=550, map_style="open-street-map")
    st.plotly_chart(fig, use_container_width=True)

with tab_quality:
    st.subheader("Data Quality Assessment (raw input)")
    qcol1, qcol2 = st.columns([1, 2])
    with qcol1:
        st.metric("Quality Score", f"{quality_report.quality_score()}/100")
        st.metric("Duplicates Removed", quality_report.duplicate_records)
        st.metric("Invalid Dates", quality_report.invalid_dates)
        st.metric("Non-standard Severities", quality_report.invalid_severities)
    with qcol2:
        st.dataframe(quality_report.summary(), use_container_width=True,
                     hide_index=True)

    st.subheader("Regulatory Compliance Checks")
    validator = ComplianceValidator(df)
    results = validator.run_all()
    st.dataframe(
        results.style.map(
            lambda v: "background-color:#d4edda" if v == "PASS"
            else ("background-color:#f8d7da" if v == "FAIL" else ""),
            subset=["status"],
        ),
        use_container_width=True, hide_index=True,
    )
    st.metric("Compliance Rate", f"{validator.compliance_rate()}%")

with tab_report:
    st.subheader("Downloadable Executive Report")

    kpis = proc.kpis()
    report_md = f"""# HSE Executive Summary

**Period:** {df['incident_date'].min().date()} to {df['incident_date'].max().date()}

| KPI | Value |
|---|---|
| Total incidents | {kpis['total_incidents']} |
| Lost Time Injuries | {kpis['lost_time_injuries']} |
| Fatalities | {kpis['fatalities']} |
| LTIFR (per 1M hours) | {kpis['ltifr']} |
| Avg days lost | {kpis['avg_days_lost']} |
| Reported within 24h | {kpis['pct_reported_24h']}% |
| Top incident type | {kpis['top_incident_type']} |
| Top root cause | {kpis['top_root_cause']} |

**Data quality score:** {quality_report.quality_score()}/100
**Compliance rate:** {ComplianceValidator(df).compliance_rate()}%
"""
    st.markdown(report_md)
    st.download_button(
        "⬇️ Download report (Markdown)",
        report_md, file_name="hse_executive_summary.md",
    )
    st.download_button(
        "⬇️ Download cleaned dataset (CSV)",
        fdf.to_csv(index=False), file_name="incidents_clean.csv",
    )
