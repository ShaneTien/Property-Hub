import json
import os
import streamlit as st
import pydeck as pdk
import pandas as pd

from config import ONEMAP_BASEMAP, LAND_USE_COLORS, DATA_SOURCES
from utils import haversine
from data_loaders import (
    load_transactions, load_masterplan,
    load_mrt_stations, load_schools, search_onemap_keyword,
    geocode_address,
)
from layers import (
    build_transaction_layer, build_masterplan_layer,
    build_mrt_layer, build_amenity_layer, build_radius_ring,
    TOOLTIP_TRANSACTIONS, TOOLTIP_MASTERPLAN,
    TOOLTIP_MRT, TOOLTIP_AMENITY, TOOLTIP_COMBINED, TOOLTIP_HEX,
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

# Sorted list of unique months for the play animation
_play_months = sorted(
    df_tx["date"].dropna().dt.to_period("M").unique().to_timestamp().tolist()
)

# ── DEFAULTS ──────────────────────────────────────────────
tx_view           = "Points"
hex_radius        = 200
grid_size         = 400
extruded          = False
max_elevation     = 500
segments          = []
prop_types        = []
sale_types        = []
date_range        = None
mp_opacity        = 0.6
show_amenities    = False
show_mrt          = False
show_hospitals    = False
show_malls        = False
show_supermarkets = False
show_schools_am   = False
school_levels     = []
show_parks        = False
show_cc           = False

# ── SIDEBAR ───────────────────────────────────────────────
with st.sidebar:

    # ── SEARCH ────────────────────────────────────────────
    st.markdown("## 📍 Search")
    search_query = st.text_input("Address or project", placeholder="e.g. Orchard Road")

    if "center_lat" not in st.session_state:
        st.session_state.center_lat       = None
        st.session_state.center_lon       = None
        st.session_state.resolved_address = None
        st.session_state.last_query       = ""

    if "play_month_idx" not in st.session_state:
        st.session_state.play_month_idx = 0
        st.session_state.is_playing     = False

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

    # ── LAYERS ────────────────────────────────────────────
    st.markdown("---")
    st.markdown("## 🗺️ Layers")

    # Master Plan
    show_mp = st.checkbox("Master Plan 2025", value=False)
    if show_mp:
        mp_opacity = st.slider(
            "Transparency", 0, 100, 60, step=5,
            key="mp_opacity", format="%d%%"
        ) / 100

    # Transactions
    show_tx = st.checkbox("Transactions", value=True)
    if show_tx:
        with st.expander("Transaction Filters"):
            tx_view = st.radio(
                "View",
                ["Points", "Heatmap", "Hexagon", "Grid"],
                horizontal=True,
            )
            if tx_view == "Hexagon":
                hex_radius = st.slider("Hex radius (m)", 25, 2000, 200, step=25)
                extruded   = st.checkbox("3D extrusion", value=False)
                if extruded:
                    max_elevation = st.slider("Max height (m)", 50, 5000, 500, step=50)
            elif tx_view == "Grid":
                grid_size = st.slider("Cell size (m)", 25, 5000, 400, step=25)
                extruded  = st.checkbox("3D extrusion", value=False)
                if extruded:
                    max_elevation = st.slider("Max height (m)", 50, 5000, 500, step=50)
            segments   = st.multiselect("Market Segment", ["CCR", "RCR", "OCR"], default=[])
            prop_types = st.multiselect("Property Type", sorted(df_tx["property_type"].dropna().unique()), default=[])
            sale_types = st.multiselect("Type of Sale", ["1 - New Sale", "2 - Sub Sale", "3 - Resale"], default=[])
            min_date = df_tx["date"].min().to_pydatetime()
            max_date = df_tx["date"].max().to_pydatetime()

            # Move slider thumb to current play month
            if st.session_state.get("is_playing") and _play_months:
                play_idx  = min(st.session_state.play_month_idx, len(_play_months) - 1)
                play_date = _play_months[play_idx]
                st.session_state["tx_date_slider"] = (play_date, play_date)

            date_range = st.slider(
                "Contract Date",
                min_value=min_date,
                max_value=max_date,
                value=(min_date, max_date),
                format="MMM YYYY",
                key="tx_date_slider",
                disabled=st.session_state.get("is_playing", False),
            )

            if st.button("⏸" if st.session_state.is_playing else "▶", key="play_btn"):
                st.session_state.is_playing = not st.session_state.is_playing
                if st.session_state.is_playing:
                    st.session_state.play_month_idx = 0

    # Amenities
    show_amenities = st.checkbox("Amenities", value=False)
    if show_amenities:
        if not center_lat:
            st.caption("⚠️ Search a location to load amenities.")
        else:
            show_mrt          = st.checkbox("🚇 MRT / LRT Stations",  value=True)
            show_hospitals    = st.checkbox("🏥 Hospitals",            value=False)
            show_malls        = st.checkbox("🛍️ Shopping Malls",       value=False)
            show_supermarkets = st.checkbox("🛒 Supermarkets",         value=False)
            show_schools_am   = st.checkbox("🏫 Schools",              value=False)
            if show_schools_am:
                school_levels = st.multiselect(
                    "School Level",
                    ["Kindergartens", "Primary School", "Secondary School",
                     "Pre-Tertiary", "Tertiary / University"],
                    default=[],
                )
            show_parks = st.checkbox("🌳 Parks",             value=False)
            show_cc    = st.checkbox("🏛️ Community Centres", value=False)

    st.markdown("---")
    if st.button("📋 Data Sources & Reference"):
        st.session_state["_open_dialog"] = True
    st.caption("Property Hub · URA · data.gov.sg")

radius_m = st.session_state.get("radius_m", 500)

# ── APPLY TRANSACTION FILTERS ─────────────────────────────
filtered = df_tx.copy()
if show_tx and st.session_state.get("is_playing") and _play_months:
    # Animation mode: single month
    play_date = _play_months[min(st.session_state.play_month_idx, len(_play_months) - 1)]
    filtered  = filtered[filtered["date"].dt.to_period("M") == pd.Period(play_date, "M")]
elif show_tx and date_range:
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
layers           = []
all_amenity_data = []

# Master Plan (full island, no location required)
if show_mp:
    with st.spinner("Loading Master Plan 2025..."):
        mp_geojson, _mp_fetched_at = load_masterplan()
    layers += build_masterplan_layer(mp_geojson, opacity=mp_opacity)

# Transactions
if show_tx:
    layers += build_transaction_layer(
        filtered, tx_view,
        hex_radius=hex_radius, grid_size=grid_size,
        extruded=extruded, max_elevation=max_elevation,
    )

# Amenities
SCHOOL_LEVEL_CODES = {
    "Kindergartens":         ["KINDERGARTEN"],
    "Primary School":        ["PRIMARY"],
    "Secondary School":      ["SECONDARY", "MIXED LEVELS"],
    "Pre-Tertiary":          ["JUNIOR COLLEGE", "CENTRALISED INSTITUTE"],
    "Tertiary / University": ["UNIVERSITY", "POLYTECHNIC", "INSTITUTE OF TECHNICAL EDUCATION"],
}

if show_amenities and center_lat:

    if show_mrt:
        with st.spinner("Loading MRT/LRT stations..."):
            mrt_stations, _ = load_mrt_stations()
        nearby_mrt = [
            s for s in mrt_stations
            if haversine(center_lat, center_lon, s["latitude"], s["longitude"]) <= radius_m
        ]
        for s in nearby_mrt:
            s["category"]     = "MRT / LRT Stations"
            s["distance"]     = haversine(center_lat, center_lon, s["latitude"], s["longitude"])
            s["walking_mins"] = round(s["distance"] / 80, 0)
        layers += build_mrt_layer(nearby_mrt)
        all_amenity_data.extend(nearby_mrt)

    if show_hospitals:
        with st.spinner("Loading hospitals..."):
            hospitals = search_onemap_keyword("hospital", center_lat, center_lon, radius_m)
        for h in hospitals:
            h["color"]        = [220, 50, 50, 240]
            h["category"]     = "Hospitals"
            h["line_label"]   = ""
            h["walking_mins"] = round(h["distance"] / 80, 0)
        layers += build_amenity_layer(hospitals)
        all_amenity_data.extend(hospitals)

    if show_malls:
        with st.spinner("Loading shopping malls..."):
            malls = search_onemap_keyword("mall", center_lat, center_lon, radius_m)
        for m in malls:
            m["color"]        = [255, 100, 0, 240]
            m["category"]     = "Shopping Malls"
            m["line_label"]   = ""
            m["walking_mins"] = round(m["distance"] / 80, 0)
        layers += build_amenity_layer(malls)
        all_amenity_data.extend(malls)

    if show_supermarkets:
        with st.spinner("Loading supermarkets..."):
            supermarkets = (
                search_onemap_keyword("fairprice",         center_lat, center_lon, radius_m) +
                search_onemap_keyword("cold storage",      center_lat, center_lon, radius_m) +
                search_onemap_keyword("giant supermarket", center_lat, center_lon, radius_m) +
                search_onemap_keyword("sheng siong",       center_lat, center_lon, radius_m)
            )
        for s in supermarkets:
            s["color"]        = [255, 150, 0, 240]
            s["category"]     = "Supermarkets"
            s["line_label"]   = ""
            s["walking_mins"] = round(s["distance"] / 80, 0)
        layers += build_amenity_layer(supermarkets)
        all_amenity_data.extend(supermarkets)

    if show_schools_am:
        with st.spinner("Loading schools..."):
            all_schools, _ = load_schools()
        level_codes = []
        for lv in (school_levels or list(SCHOOL_LEVEL_CODES)):
            level_codes.extend(SCHOOL_LEVEL_CODES.get(lv, []))
        nearby_schools = [
            s for s in all_schools
            if haversine(center_lat, center_lon, s["latitude"], s["longitude"]) <= radius_m
            and (not level_codes or s.get("level", "") in level_codes)
        ]
        for s in nearby_schools:
            s["color"]        = [0, 153, 0, 240]
            s["category"]     = "Schools"
            s["line_label"]   = s.get("level", "")
            s["distance"]     = haversine(center_lat, center_lon, s["latitude"], s["longitude"])
            s["walking_mins"] = round(s["distance"] / 80, 0)
        layers += build_amenity_layer(nearby_schools)
        all_amenity_data.extend(nearby_schools)

    if show_parks:
        with st.spinner("Loading parks..."):
            parks = search_onemap_keyword("park", center_lat, center_lon, radius_m)
        for p in parks:
            p["color"]        = [0, 102, 0, 240]
            p["category"]     = "Parks"
            p["line_label"]   = ""
            p["walking_mins"] = round(p["distance"] / 80, 0)
        layers += build_amenity_layer(parks)
        all_amenity_data.extend(parks)

    if show_cc:
        with st.spinner("Loading community centres..."):
            cc_raw = (
                search_onemap_keyword("community centre", center_lat, center_lon, radius_m) +
                search_onemap_keyword("community club",   center_lat, center_lon, radius_m)
            )
        seen, cc = set(), []
        for item in cc_raw:
            if item["name"] not in seen:
                seen.add(item["name"])
                cc.append(item)
        for c in cc:
            c["color"]        = [0, 180, 180, 240]
            c["category"]     = "Community Centres"
            c["line_label"]   = ""
            c["walking_mins"] = round(c["distance"] / 80, 0)
        layers += build_amenity_layer(cc)
        all_amenity_data.extend(cc)

# Radius ring (on top)
if center_lat:
    layers += build_radius_ring(center_lat, center_lon, radius_m)

# ── MAP ───────────────────────────────────────────────────
view_state = pdk.ViewState(
    latitude=center_lat  if center_lat else 1.3521,
    longitude=center_lon if center_lon else 103.8198,
    zoom=14 if center_lat else 11,
    pitch=45 if extruded else 0,
)

active_layers = [show_tx, show_mp, show_amenities and bool(all_amenity_data)]
if sum(active_layers) > 1:
    active_tooltip = TOOLTIP_COMBINED
elif show_mp:
    active_tooltip = TOOLTIP_MASTERPLAN
elif show_amenities and all_amenity_data:
    active_tooltip = TOOLTIP_AMENITY
elif show_tx and tx_view in ("Hexagon", "Grid"):
    active_tooltip = TOOLTIP_HEX
else:
    active_tooltip = TOOLTIP_TRANSACTIONS

st.pydeck_chart(pdk.Deck(
    layers=layers,
    initial_view_state=view_state,
    tooltip=active_tooltip,
    map_style=ONEMAP_BASEMAP,
), height=650)

if show_tx and st.session_state.get("is_playing") and _play_months:
    cur = _play_months[min(st.session_state.play_month_idx, len(_play_months) - 1)]
    st.markdown(f"### ▶ {cur.strftime('%B %Y')} — {len(filtered):,} transactions")

if show_tx and len(filtered) > 0:
    if tx_view == "Points":
        st.markdown("🟢 Low PSF &nbsp;&nbsp;&nbsp; 🔴 High PSF")
    elif tx_view in ("Hexagon", "Grid"):
        st.markdown("🟦 Low count &nbsp;&nbsp;&nbsp; 🟥 High count &nbsp;&nbsp;&nbsp; Colour and height = transaction density")

# ── MASTER PLAN LEGEND ────────────────────────────────────
if show_mp:
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

# ── AMENITIES TABLE ───────────────────────────────────────
if show_amenities and all_amenity_data:
    st.markdown("---")
    st.markdown("### 📍 Nearby Amenities")
    rows = [{
        "Name":         a.get("name", ""),
        "Type":         a.get("line_label") or a.get("category", ""),
        "Category":     a.get("category", ""),
        "Distance (m)": int(round(a.get("distance", 0))),
        "Walk (mins)":  int(round(a.get("distance", 0) / 80)),
    } for a in all_amenity_data]
    amenity_df = pd.DataFrame(rows).sort_values(["Category", "Distance (m)"]).reset_index(drop=True)
    for category, group in amenity_df.groupby("Category"):
        with st.expander(f"{category} ({len(group)})"):
            st.dataframe(
                group[["Name", "Type", "Distance (m)", "Walk (mins)"]].reset_index(drop=True),
                use_container_width=True,
                hide_index=True,
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
        mp_geojson,   mp_fetched  = load_masterplan()
        mrt_stations, mrt_fetched = load_mrt_stations()
        all_schools,  sch_fetched = load_schools()

    def _fmt(ts):
        return ts.strftime("%d %b %Y, %H:%M") if ts else "—"

    def _csv(rows):
        return pd.DataFrame(rows).to_csv(index=False).encode("utf-8")

    mrt_csv = _csv([{
        "name": s["name"], "rail_type": s.get("rail_type", ""),
        "latitude": s["latitude"], "longitude": s["longitude"],
    } for s in mrt_stations]) if mrt_stations else None

    sch_csv = _csv([{
        "name": s["name"], "level": s.get("level", ""),
        "latitude": s["latitude"], "longitude": s["longitude"],
    } for s in all_schools]) if all_schools else None

    downloads = {
        "ura_transactions": (df_tx.to_csv(index=False).encode("utf-8"), "ura_transactions.csv",   "text/csv",              tx_pulled),
        "masterplan":       (json.dumps(mp_geojson).encode("utf-8") if mp_geojson else None,
                             "masterplan_2025.geojson", "application/geo+json", _fmt(mp_fetched)),
        "mrt":              (mrt_csv, "mrt_stations.csv",  "text/csv",              _fmt(mrt_fetched)),
        "schools":          (sch_csv, "schools.csv",       "text/csv",              _fmt(sch_fetched)),
    }

    for row in DATA_SOURCES:
        host_updated                        = tx_pulled if row["updated"] is None else row["updated"]
        dl_key                              = row.get("dl_key")
        dl_bytes, dl_file, dl_mime, pulled  = downloads.get(dl_key, (None, None, None, "—"))

        col_left, col_right = st.columns([3, 2])
        with col_left:
            st.markdown(f"**{row['layer']}**")
            st.markdown(f"[{row['source']}]({row['url']})")
            st.caption(f"Host updated: {host_updated}")
        with col_right:
            st.code(row.get("api", "—"), language=None)
            st.caption(f"Last pulled: {pulled if dl_key else '—'}")
            if dl_bytes:
                st.download_button("⬇️ Download", data=dl_bytes, file_name=dl_file,
                                   mime=dl_mime, key=f"dl_{dl_key}")
            elif dl_key is None:
                st.caption("Live search — no static dataset")
        st.divider()

# ── ANIMATION ADVANCE ────────────────────────────────────
if st.session_state.get("is_playing") and show_tx and _play_months:
    import time
    time.sleep(0.5)
    next_idx = st.session_state.play_month_idx + 1
    if next_idx >= len(_play_months):
        st.session_state.is_playing = False
        st.session_state["tx_date_slider"] = (_tx_min.to_pydatetime(), _tx_max.to_pydatetime())
    else:
        st.session_state.play_month_idx = next_idx
    st.rerun()

if st.session_state.get("_open_dialog"):
    st.session_state["_open_dialog"] = False
    _show_data_sources_dialog(df_tx=df_tx, csv_mtime=_csv_mtime, tx_min=_tx_min, tx_max=_tx_max)
