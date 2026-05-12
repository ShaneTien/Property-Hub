import altair as alt
import numpy as np
import pandas as pd
import streamlit as st


def chart_psf_trend(filtered):
    trend = (
        filtered.groupby("date")["psf"]
        .median()
        .reset_index()
        .rename(columns={"date": "Date", "psf": "Median PSF"})
    )
    return alt.Chart(trend).mark_line(point=True, color="#E8542A").encode(
        x=alt.X("Date:T", title="", axis=alt.Axis(format="%b %Y", labelAngle=-45)),
        y=alt.Y("Median PSF:Q", title="Median PSF (S$)"),
        tooltip=[
            alt.Tooltip("Date:T", format="%b %Y"),
            alt.Tooltip("Median PSF:Q", format=",.0f")
        ]
    ).properties(height=300)


def chart_volume(filtered):
    vol = (
        filtered.groupby("date")
        .size()
        .reset_index(name="Transactions")
        .rename(columns={"date": "Date"})
    )
    return alt.Chart(vol).mark_bar(color="#4C78A8").encode(
        x=alt.X("Date:T", title="", axis=alt.Axis(format="%b %Y", labelAngle=-45)),
        y=alt.Y("Transactions:Q", title="Transactions"),
        tooltip=[
            alt.Tooltip("Date:T", format="%b %Y"),
            "Transactions:Q"
        ]
    ).properties(height=300)


def chart_psf_distribution(filtered):
    psf_vals = filtered["psf"].dropna()
    hist, edges = np.histogram(psf_vals, bins=40)
    hist_df = pd.DataFrame({
        "PSF":   edges[:-1].astype(int),
        "Count": hist
    })
    return alt.Chart(hist_df).mark_bar(color="#72B7B2").encode(
        x=alt.X("PSF:Q", title="PSF (S$)", axis=alt.Axis(format=",.0f")),
        y=alt.Y("Count:Q", title="Transactions"),
        tooltip=[
            alt.Tooltip("PSF:Q", format=",.0f"),
            "Count:Q"
        ]
    ).properties(height=300)


def chart_by_property_type(filtered):
    by_type = (
        filtered.groupby("property_type")["psf"]
        .median()
        .sort_values(ascending=False)
        .reset_index()
        .rename(columns={"property_type": "Property Type", "psf": "Median PSF"})
    )
    return alt.Chart(by_type).mark_bar(color="#F58518").encode(
        x=alt.X("Median PSF:Q", title="Median PSF (S$)", axis=alt.Axis(format=",.0f")),
        y=alt.Y("Property Type:N", sort="-x", title=""),
        tooltip=[
            "Property Type:N",
            alt.Tooltip("Median PSF:Q", format=",.0f")
        ]
    ).properties(height=250)


def render_charts(filtered):
    # Summary stats
    psf = filtered["psf"].dropna()
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Transactions", f"{len(filtered):,}")
    col2.metric("Mean PSF",     f"S${psf.mean():,.0f}")
    col3.metric("Median PSF",   f"S${psf.median():,.0f}")
    col4.metric("25th Pctile",  f"S${psf.quantile(0.25):,.0f}")
    col5.metric("75th Pctile",  f"S${psf.quantile(0.75):,.0f}")
    st.markdown("---")

    st.markdown("### 📊 Transaction Analysis")

    # Combined PSF trend + volume overlay
    trend = (
        filtered.groupby("date")
        .agg(median_psf=("psf", "median"), transactions=("psf", "count"))
        .reset_index()
        .rename(columns={"date": "Date"})
    )

    base = alt.Chart(trend).encode(
        x=alt.X("Date:T", title="", axis=alt.Axis(format="%b %Y", labelAngle=-45))
    )

    line = base.mark_line(point=True, color="#E8542A").encode(
        y=alt.Y("median_psf:Q", title="Median PSF (S$)", axis=alt.Axis(titleColor="#E8542A")),
        tooltip=[
            alt.Tooltip("Date:T", format="%b %Y"),
            alt.Tooltip("median_psf:Q", title="Median PSF", format=",.0f"),
            alt.Tooltip("transactions:Q", title="Transactions"),
        ]
    )

    bars = base.mark_bar(opacity=0.3, color="#4C78A8").encode(
        y=alt.Y("transactions:Q", title="Transactions", axis=alt.Axis(titleColor="#4C78A8")),
        tooltip=[
            alt.Tooltip("Date:T", format="%b %Y"),
            alt.Tooltip("transactions:Q", title="Transactions"),
            alt.Tooltip("median_psf:Q", title="Median PSF", format=",.0f"),
        ]
    )

    chart = alt.layer(bars, line).resolve_scale(y="independent").properties(height=350)
    st.altair_chart(chart, use_container_width=True)

    st.markdown("---")
    with st.expander("View transaction data"):
        st.dataframe(
            filtered[[
                "project", "street", "district", "market_segment",
                "property_type", "tenure", "floor_range",
                "area_sqft", "psf", "price_sgd", "type_of_sale", "date"
            ]]
            .sort_values("date", ascending=False)
            .reset_index(drop=True),
            use_container_width=True
        )
