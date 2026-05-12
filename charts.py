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
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Transactions", f"{len(filtered):,}")
    col2.metric("Median PSF",   f"S${filtered['psf'].median():,.0f}")
    col3.metric("Median Price", f"S${filtered['price_sgd'].median()/1e6:.2f}M")
    col4.metric("Avg Area",     f"{filtered['area_sqft'].mean():,.0f} sqft")
    st.markdown("---")

    # Charts
    st.markdown("### 📊 Transaction Analysis")
    tab1, tab2, tab3, tab4 = st.tabs([
        "PSF Trend", "Volume", "PSF Distribution", "By Property Type"
    ])
    with tab1:
        st.altair_chart(chart_psf_trend(filtered), use_container_width=True)
    with tab2:
        st.altair_chart(chart_volume(filtered), use_container_width=True)
    with tab3:
        st.altair_chart(chart_psf_distribution(filtered), use_container_width=True)
    with tab4:
        st.altair_chart(chart_by_property_type(filtered), use_container_width=True)

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
