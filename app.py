import streamlit as st
import pydeck as pdk
import pandas as pd

from config import ONEMAP_BASEMAP, AMENITY_CATEGORY_COLORS, MRT_COLOR, LAND_USE_COLORS, DATA_SOURCES
from utils import haversine, bbox
from data_loaders import (
    load_transactions, load_gls, load_masterplan,
    load_mrt_stations, get_onemap_token,
    geocode_address, load_amenities_onemap, load_onemap_themes
)
from layers import (
    build_transaction_layer, build_gls_layer,
    build_masterplan_layer, build_amenity_layer,
    build_radius_ring, TOOLTIP
)
from charts import render_charts

st.set_page_config(page_title="Property Hub", page_icon="🏙️", layout="wide")
st.title("🏙️ Property Hub")

# ── ACCESS KEYS ──────────────────────────────────────────
try:
    access_key = st.secrets["URA_ACCESS_KEY"]
except:
    access_key = st.sidebar.text_input("URA Access Key", type="password")
    if not access_key:
        st.warning("Enter your URA Access Key in the sidebar.")
        st.stop()

try:
    onemap_token = get_onemap_token(
        st.secrets["ONEMAP_EMAIL"],
        st.secrets["ONEMAP_PASSWORD"]
    )
except:
    onemap_token = None

# ── LOAD TRANSACTIONS ────────────────────────────────────
with st.spinner("Loading URA transaction data..."):
    df_tx = load_transactions(access_key)

# ── SIDEBAR: SEARCH ──────────────────────────────────────
st.sidebar.markdown("## 🔍 Location Search")
search_query = st.sidebar.text_input("Search address or project", placeholder="e.g. Orchard Road")
radius_m     = st.sidebar.slider("Search radius (m)", 250, 2000, 500, step=250)

center_lat, center_lon, resolved_address = None, None, None
if search_query:
    center_lat, center_lon, resolved_address = geocode_address(search_query)
    if center_lat:
        st.sidebar.success(f"📍 {resolved_address}")
    else:
        st.sidebar.error("Address not found.")

# ── SIDEBAR: LAYERS ──────────────────────────────────────
st.sidebar.markdown("---")
st.sidebar.markdown("## 🗂️ Layers")
show_tx        = st.sidebar.checkbox("Transactions", value=False)
tx_view        = st.sidebar.radio("View", ["Points", "Heatmap"], horizontal=True) if show_tx else "Points"
show_gls       = st.sidebar.checkbox("GLS Sites", value=False)
show_mp        = st.sidebar.checkbox("Master Plan 2025", value=False)
show_amenities = st.sidebar.checkbox("Amenities", value=False)
amenity_radius_m = st.sidebar.slider("Amenity radius (m)", 250, 2000, 1000, step=250) if show_amenities else 1000

# Amenity theme selection
selected_themes = {}
show_mrt = False
if show_amenities and center_lat and onemap_token:
    with st.sidebar.expander("🚇 Transport (MRT/LRT)"):
        show_mrt = st.checkbox("MRT / LRT Stations", value=True, key="am_mrt")

    with st.spinner("Loading theme list..."):
        grouped_themes = load_onemap_themes(onemap_token)

    for category, themes in sorted(grouped_themes.items()):
        color = AMENITY_CATEGORY_COLORS.get(category, [180, 180, 180, 240])
        with st.sidebar.expander(f"{category} ({len(themes)})"):
            for theme in sorted(themes, key=lambda x: x["name"]):
                checked = st.checkbox(
                    theme["name"],
                    value=False,
                    key=f"am_{theme['queryName']}"
                )
                if checked:
                    selected_themes[theme["queryName"]] = color
elif show_amenities and not center_lat:
    st.sidebar.warning("Search a location to load amenities.")

# ── SIDEBAR: FILTERS ─────────────────────────────────────
st.sidebar.markdown("---")
st.sidebar.markdown("## 🔧 Filters")
segments   = st.sidebar.multiselect("Market Segment", ["CCR", "RCR", "OCR"], default=[])
prop_types = st.sidebar.multiselect("Property Type", sorted(df_tx["property_type"].dropna().unique()), default=[])
sale_types = st.sidebar.multiselect("Type of Sale", ["1 - New Sale", "2 - Sub Sale", "3 - Resale"], default=[])
min_date   = df_tx["date"].min().to_pydatetime()
max_date   = df_tx["date"].max().to_pydatetime()
date_range = st.sidebar.slider("Contract Date", min_value=min_date, max_value=max_date, value=(min_date, max_date), format="MMM YYYY")
psf_min, psf_max = int(df_tx["psf"].min()), int(df_tx["psf"].max())
psf_range  = st.sidebar.slider("PSF (S$)", psf_min, psf_max, (psf_min, psf_max))

# ── APPLY FILTERS ────────────────────────────────────────
filtered = df_tx.copy()
filtered = filtered[(filtered["date"] >= date_range[0]) & (filtered["date"] <= date_range[1])]
filtered = filtered[(filtered["psf"] >= psf_range[0]) & (filtered["psf"] <= psf_range[1])]
if segments:
    filtered = filtered[filtered["market_segment"].isin(segments)]
if prop_types:
    filtered = filtered[filtered["property_type"].isin(prop_types)]
if sale_types:
    sale_map = {"1 - New Sale": "1", "2 - Sub Sale": "2", "3 - Resale": "3"}
    filtered = filtered[filtered["type_of_sale"].isin([sale_map[s] for s in sale_types])]
filtered = filtered[filtered["latitude"].notna()]
if center_lat:
    filtered["distance_m"] = filtered.apply(
        lambda r: haversine(center_lat, center_lon, r["latitude"], r["longitude"]), axis=1
    )
    filtered = filtered[filtered["distance_m"] <= radius_m]

# ── BUILD LAYERS ─────────────────────────────────────────
layers = []

# Master Plan
if show_mp:
    if not center_lat:
        st.warning("⚠️ Search a location first to load Master Plan.")
    else:
        with st.spinner("Loading Master Plan 2025..."):
            mp_geojson = load_masterplan()
        layers += build_masterplan_layer(mp_geojson, center_lat, center_lon, radius_m)

# GLS
if show_gls:
    with st.spinner("Loading GLS sites..."):
        gls_geojson = load_gls()
    layers += build_gls_layer(gls_geojson)

# Transactions
if show_tx:
    layers += build_transaction_layer(filtered, tx_view)

# Amenities
if show_amenities and center_lat and onemap_token:
    amenity_data = []

    # MRT from data.gov.sg
    if show_mrt:
        with st.spinner("Loading MRT stations..."):
            mrt_stations = load_mrt_stations()
        lat1, lon1, lat2, lon2 = bbox(center_lat, center_lon, amenity_radius_m)
        nearby_mrt = [
            s for s in mrt_stations
            if lat1 <= s["latitude"] <= lat2 and lon1 <= s["longitude"] <= lon2
        ]
        amenity_data.extend(nearby_mrt)

    # Selected OneMap themes
    if selected_themes:
        items = load_amenities_onemap(
            onemap_token,
            list(selected_themes.keys()),
            center_lat, center_lon, amenity_radius_m
        )
        for item in items:
            item["color"] = selected_themes.get(item["theme"], [180, 180, 180, 240])
            item["group"] = item["theme"]
        amenity_data.extend(items)

    layers += build_amenity_layer(amenity_data)
    if amenity_data:
        st.sidebar.markdown(f"**{len(amenity_data):,} amenities found**")

# Radius ring
if center_lat:
    layers += build_radius_ring(center_lat, center_lon, radius_m)

# ── MAP ──────────────────────────────────────────────────
view_state = pdk.ViewState(
    latitude=center_lat  if center_lat else 1.3521,
    longitude=center_lon if center_lon else 103.8198,
    zoom=14 if center_lat else 11,
    pitch=0,
)

st.pydeck_chart(pdk.Deck(
    layers=layers,
    initial_view_state=view_state,
    tooltip=TOOLTIP,
    map_style=ONEMAP_BASEMAP,
))

if show_tx and tx_view == "Points" and len(filtered) > 0:
    st.markdown("🟢 Low PSF &nbsp;&nbsp;&nbsp; 🔴 High PSF")

# ── MASTER PLAN LEGEND ───────────────────────────────────
if show_mp and center_lat:
    with st.expander("Master Plan Legend"):
        cols = st.columns(4)
        for i, (lu, color) in enumerate(LAND_USE_COLORS.items()):
            hex_color  = "#{:02x}{:02x}{:02x}".format(color[0], color[1], color[2])
            text_color = "#000" if sum(color[:3]) > 400 else "#fff"
            cols[i % 4].markdown(
                f"<span style='background:{hex_color};padding:2px 8px;"
                f"border-radius:3px;font-size:11px;color:{text_color}'>{lu}</span>",
                unsafe_allow_html=True
            )

# ── CHARTS ───────────────────────────────────────────────
if show_tx and len(filtered) > 0:
    st.markdown("---")
    render_charts(filtered)

# ── SIDEBAR: DATA SUMMARY ────────────────────────────────
st.sidebar.markdown("---")
st.sidebar.markdown("## 📋 Data Sources")
for row in DATA_SOURCES:
    st.sidebar.markdown(f"**{row['Layer']}** · {row['Source']}  \n*Updated: {row['Updated']}*")

st.sidebar.caption("Property Hub · URA · OneMap · data.gov.sg")
