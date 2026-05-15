import json
import os
import streamlit as st
import pydeck as pdk
import pandas as pd

from config import ONEMAP_BASEMAP, LAND_USE_COLORS, DATA_SOURCES
from utils import haversine
from data_loaders import load_transactions, load_masterplan, geocode_address
from layers import (
    build_transaction_layer, build_masterplan_layer, build_radius_ring,
    TOOLTIP_TRANSACTIONS, TOOLTIP_MASTERPLAN, TOOLTIP_MIXED,
)
from charts import render_charts

st.set_page_config(page_title="Property Hub", page_icon="🏙️", layout="wide")
st.markdown("""
    <style>
        .block-container { padding-top: 1rem; }
    </style>
""", unsafe_allow_html=True)
st.title("🏙️ Property Hub")

# ── ACCESS KEY ────────────────────────────────────────────
try:
    access_key = st.secrets["URA_ACCESS_KEY"]
except:
    access_key = st.sidebar.text_input("URA Access Key", type="password")
    if not access_key:
        st.warning("Enter your URA Access Key in the sidebar.")
        st.stop()

# ── LOAD TRANSACTIONS ─────────────────────────────────────
with st.spinner("Loading URA transaction data..."):
    df_tx, _tx_fetched_at = load_transactions(access_key)

_csv_path  = os.path.join(os.path.dirname(__file__), "data", "ura_transactions.csv")
_csv_mtime = (
    pd.Timestamp(os.path.getmtime(_csv_path), unit="s", tz="UTC").tz_localize(None)
    if os.path.exists(_csv_path) else None
)
_tx_min = df_tx["date"].dropna().min()
_tx_max = df_tx["date"].dropna().max()

# ── SIDEBAR ───────────────────────────────────────────────
with st.sidebar:
    tab_search, tab_layers = st.tabs(["📍 Search", "🗺️ Layers"])

    # ── SEARCH TAB ────────────────────────────────────────
    with tab_search:
        search_query = st.text_input("Address or project", placeholder="e.g. Orchard Road")

        if "center_lat" not in st.session_state:
            st.session_state.center_lat       = None
            st.session_state.center_lon       = None
            st.session_state.resolved_address = None
            st.session_state.last_query       = ""

        if search_query and search_query != st.session_state.last_query:
            lat, lon, addr = geocode_address(search_query)
            if lat:
                st.session_state.center_lat       = lat
                st.session_state.center_lon       = lon
                st.session_state.resolved_address = addr
                st.session_state.last_query       = search_query
            else:
                st.session_state.center_lat       = None
                st.session_state.center_lon       = None
                st.session_state.resolved_address = None
                st.session_state.last_query       = search_query

        if not search_query:
            st.session_state.center_lat       = None
            st.session_state.center_lon       = None
            st.session_state.resolved_address = None
            st.session_state.last_query       = ""

        center_lat       = st.session_state.center_lat
        center_lon       = st.session_state.center_lon
        resolved_address = st.session_state.resolved_address

        if center_lat:
            st.success(f"📍 {resolved_address}")
        elif search_query:
            st.error("Address not found.")

        st.slider("Radius (m)", 250, 2000, 500, step=250, key="radius_m")

    # ── LAYERS TAB ────────────────────────────────────────
    with tab_layers:
        show_tx = st.checkbox("Transactions", value=True)
        tx_view = "Points"
        segments, prop_types, sale_types = [], [], []
        date_range = None

        if show_tx:
            with st.expander("Transaction Filters"):
                tx_view    = st.radio("View", ["Points", "Heatmap"], horizontal=True)
                segments   = st.multiselect("Market Segment", ["CCR", "RCR", "OCR"], default=[])
                prop_types = st.multiselect("Property Type", sorted(df_tx["property_type"].dropna().unique()), default=[])
                sale_types = st.multiselect("Type of Sale", ["1 - New Sale", "2 - Sub Sale", "3 - Resale"], default=[])
                min_date   = df_tx["date"].min().to_pydatetime()
                max_date   = df_tx["date"].max().to_pydatetime()
                date_range = st.slider("Contract Date", min_value=min_date, max_value=max_date, value=(min_date, max_date), format="MMM YYYY")

        show_mp    = st.checkbox("Master Plan 2025", value=False)
        mp_opacity = 0.6
        if show_mp:
            mp_opacity = st.slider("Transparency", 0, 100, 60, step=5, key="mp_opacity",
                                   format="%d%%") / 100

    st.markdown("---")
    if st.button("📋 Data Sources & Reference"):
        st.session_state["_open_dialog"] = True
    st.caption("Property Hub · URA · data.gov.sg")

radius_m = st.session_state.get("radius_m", 500)

# ── APPLY TRANSACTION FILTERS ─────────────────────────────
filtered = df_tx.copy()
if show_tx and date_range:
    filtered = filtered[(filtered["date"] >= date_range[0]) & (filtered["date"] <= date_range[1])]
if segments:
    filtered = filtered[filtered["market_segment"].isin(segments)]
if prop_types:
    filtered = filtered[filtered["property_type"].isin(prop_types)]
if sale_types:
    sale_map   = {"1 - New Sale": "1", "2 - Sub Sale": "2", "3 - Resale": "3"}
    sale_codes = [sale_map[s] for s in sale_types]
    filtered   = filtered[filtered["type_of_sale"].astype(str).isin(sale_codes)]
filtered = filtered[filtered["latitude"].notna()]
if center_lat and show_tx:
    filtered["distance_m"] = filtered.apply(
        lambda r: haversine(center_lat, center_lon, r["latitude"], r["longitude"]), axis=1
    )
    filtered = filtered[filtered["distance_m"] <= radius_m]

# ── BUILD LAYERS ──────────────────────────────────────────
layers = []

if show_mp:
    if not center_lat:
        st.warning("⚠️ Search a location to load Master Plan.")
    else:
        with st.spinner("Loading Master Plan 2025..."):
            mp_geojson, _mp_fetched_at = load_masterplan()
        layers += build_masterplan_layer(mp_geojson, center_lat, center_lon, radius_m, opacity=mp_opacity)

if show_tx:
    layers += build_transaction_layer(filtered, tx_view)

if center_lat:
    layers += build_radius_ring(center_lat, center_lon, radius_m)

# ── MAP ───────────────────────────────────────────────────
view_state = pdk.ViewState(
    latitude=center_lat  if center_lat else 1.3521,
    longitude=center_lon if center_lon else 103.8198,
    zoom=14 if center_lat else 11,
    pitch=0,
)

if show_mp and show_tx:
    active_tooltip = TOOLTIP_MIXED
elif show_mp:
    active_tooltip = TOOLTIP_MASTERPLAN
else:
    active_tooltip = TOOLTIP_TRANSACTIONS

st.pydeck_chart(pdk.Deck(
    layers=layers,
    initial_view_state=view_state,
    tooltip=active_tooltip,
    map_style=ONEMAP_BASEMAP,
), height=650)

if show_tx and tx_view == "Points" and len(filtered) > 0:
    st.markdown("🟢 Low PSF &nbsp;&nbsp;&nbsp; 🔴 High PSF")

# ── MASTER PLAN LEGEND ────────────────────────────────────
if show_mp and center_lat:
    with st.expander("Master Plan 2025 — Land Use Legend"):
        cols = st.columns(4)
        for i, (lu, color) in enumerate(LAND_USE_COLORS.items()):
            hex_color  = "#{:02x}{:02x}{:02x}".format(color[0], color[1], color[2])
            text_color = "#000" if sum(color[:3]) > 400 else "#fff"
            cols[i % 4].markdown(
                f"<span style='background:{hex_color};padding:2px 8px;"
                f"border-radius:3px;font-size:11px;color:{text_color}'>{lu}</span>",
                unsafe_allow_html=True,
            )

# ── CHARTS ────────────────────────────────────────────────
if show_tx and len(filtered) > 0:
    st.markdown("---")
    render_charts(filtered)

# ── DATA SOURCES DIALOG ───────────────────────────────────
@st.dialog("Data Sources & Reference", width="large")
def _show_data_sources_dialog(df_tx, csv_mtime, tx_min, tx_max):
    tx_pulled = (
        csv_mtime.strftime("%d %b %Y, %H:%M") if csv_mtime is not None
        else (
            f"{tx_min.strftime('%b %Y')} – {tx_max.strftime('%b %Y')}"
            if pd.notna(tx_min) and pd.notna(tx_max) else "—"
        )
    )

    with st.spinner("Preparing downloads..."):
        mp_geojson, mp_fetched = load_masterplan()

    def _fmt(ts):
        return ts.strftime("%d %b %Y, %H:%M") if ts else "—"

    downloads = {
        "ura_transactions": (df_tx.to_csv(index=False).encode("utf-8"), "ura_transactions.csv", "text/csv", tx_pulled),
        "masterplan":       (json.dumps(mp_geojson).encode("utf-8") if mp_geojson else None, "masterplan_2025.geojson", "application/geo+json", _fmt(mp_fetched)),
    }

    for row in DATA_SOURCES:
        host_updated = tx_pulled if row["updated"] is None else row["updated"]
        dl_bytes, dl_file, dl_mime, pulled_str = downloads.get(row["dl_key"], (None, None, None, "—"))

        col_left, col_right = st.columns([3, 2])
        with col_left:
            st.markdown(f"**{row['layer']}**")
            st.markdown(f"[{row['source']}]({row['url']})")
            st.caption(f"Host updated: {host_updated}")
        with col_right:
            st.code(row.get("api", "—"), language=None)
            st.caption(f"Last pulled: {pulled_str}")
            if dl_bytes:
                st.download_button(
                    "⬇️ Download",
                    data=dl_bytes,
                    file_name=dl_file,
                    mime=dl_mime,
                    key=f"dl_{row['dl_key']}",
                )
        st.divider()

if st.session_state.get("_open_dialog"):
    st.session_state["_open_dialog"] = False
    _show_data_sources_dialog(
        df_tx=df_tx,
        csv_mtime=_csv_mtime,
        tx_min=_tx_min,
        tx_max=_tx_max,
    )
