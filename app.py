import json
import os
import streamlit as st
import pydeck as pdk
import pandas as pd

from config import ONEMAP_BASEMAP, AMENITY_CATEGORY_COLORS, LAND_USE_COLORS, DATA_SOURCES
from utils import haversine
from data_loaders import (
    load_transactions, load_gls, load_masterplan,
    load_mrt_stations, get_onemap_token,
    geocode_address, load_amenities_onemap,
    load_onemap_themes, search_onemap_keyword, load_schools,
    load_planning_area_boundaries, load_demographics, build_planning_area_data
)
from layers import (
    build_transaction_layer, build_gls_layer,
    build_masterplan_layer, build_amenity_layer,
    build_mrt_layer, build_radius_ring,
    build_demographics_layer,
    TOOLTIP_TRANSACTIONS, TOOLTIP_GLS, TOOLTIP_MASTERPLAN,
    TOOLTIP_MRT, TOOLTIP_AMENITY, TOOLTIP_DEMOGRAPHICS
)
from charts import render_charts

st.set_page_config(page_title="Property Hub", page_icon="🏙️", layout="wide")
st.markdown("""
    <style>
        .block-container { padding-top: 1rem; }
    </style>
""", unsafe_allow_html=True)
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
    df_tx, _tx_fetched_at = load_transactions(access_key)

_csv_path  = os.path.join(os.path.dirname(__file__), "data", "ura_transactions.csv")
_csv_mtime = (
    pd.Timestamp(os.path.getmtime(_csv_path), unit="s", tz="UTC").tz_localize(None)
    if os.path.exists(_csv_path) else None
)
_tx_min = df_tx["date"].dropna().min()
_tx_max = df_tx["date"].dropna().max()

# ── SIDEBAR: SEARCH ──────────────────────────────────────
st.sidebar.markdown("## 🔍 Location Search")
search_query = st.sidebar.text_input("Search address or project", placeholder="e.g. Orchard Road")

# Persist geocoded location across reruns
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
    st.sidebar.success(f"📍 {resolved_address}")
elif search_query:
    st.sidebar.error("Address not found.")

# ── SINGLE RADIUS ─────────────────────────────────────────
radius_m = st.sidebar.slider("Radius (m)", 250, 2000, 500, step=250)

# ── SIDEBAR: LAYERS ──────────────────────────────────────
st.sidebar.markdown("---")
st.sidebar.markdown("## 🗂️ Layers")

# ── TRANSACTIONS ─────────────────────────────────────────
show_tx   = st.sidebar.checkbox("Transactions", value=False)
tx_view   = "Points"
segments, prop_types, sale_types = [], [], []
date_range = None

if show_tx:
    with st.sidebar.expander("Transaction Filters"):
        tx_view    = st.radio("View", ["Points", "Heatmap"], horizontal=True)
        segments   = st.multiselect("Market Segment", ["CCR", "RCR", "OCR"], default=[])
        prop_types = st.multiselect("Property Type", sorted(df_tx["property_type"].dropna().unique()), default=[])
        sale_types = st.multiselect("Type of Sale", ["1 - New Sale", "2 - Sub Sale", "3 - Resale"], default=[])
        min_date   = df_tx["date"].min().to_pydatetime()
        max_date   = df_tx["date"].max().to_pydatetime()
        date_range = st.slider("Contract Date", min_value=min_date, max_value=max_date, value=(min_date, max_date), format="MMM YYYY")


# ── GLS ──────────────────────────────────────────────────
show_gls = st.sidebar.checkbox("GLS Sites", value=False)

# ── MASTER PLAN ──────────────────────────────────────────
show_mp  = st.sidebar.checkbox("Master Plan 2025", value=False)

# ── DEMOGRAPHICS ─────────────────────────────────────────
show_demo    = st.sidebar.checkbox("Demographics", value=False)
demo_metric  = "density"

if show_demo:
    with st.sidebar.expander("Demographics Settings"):
        demo_metric = st.radio(
            "Show by",
            ["density", "age", "dwelling"],
            format_func=lambda x: {
                "density": "Population Density",
                "age":     "% Elderly (65+)",
                "dwelling":"% Private Housing"
            }[x],
            horizontal=False
        )

# ── AMENITIES ────────────────────────────────────────────
show_amenities    = st.sidebar.checkbox("Amenities", value=False)
selected_themes   = {}
show_mrt          = False
show_malls        = False
show_supermarkets = False
show_schools      = False

if show_amenities:
    with st.sidebar.expander("Amenity Filters"):
        if center_lat and onemap_token:
            show_mrt          = st.checkbox("🚇 MRT / LRT Stations",  value=True,  key="am_mrt")
            show_malls        = st.checkbox("🛍️ Shopping Malls",       value=False, key="am_malls")
            show_supermarkets = st.checkbox("🛒 Supermarkets",         value=False, key="am_supermarkets")
            show_schools      = st.checkbox("🏫 Schools (MOE)",        value=False, key="am_schools")

            st.markdown("**OneMap Themes**")
            with st.spinner("Loading theme list..."):
                grouped_themes = load_onemap_themes(onemap_token)

            for category, themes in sorted(grouped_themes.items()):
                color = AMENITY_CATEGORY_COLORS.get(category, [180, 180, 180, 240])
                with st.expander(f"{category} ({len(themes)})"):
                    select_all = st.checkbox("Select all", value=False, key=f"am_all_{category}")
                    for theme in sorted(themes, key=lambda x: x["name"]):
                        checked = st.checkbox(theme["name"], value=select_all, key=f"am_{theme['queryName']}")
                        if checked:
                            selected_themes[theme["queryName"]] = color
        elif center_lat and not onemap_token:
            st.warning("OneMap credentials missing.")
        else:
            st.warning("Search a location to load amenities.")

# ── APPLY TRANSACTION FILTERS ────────────────────────────
filtered = df_tx.copy()
if show_tx and date_range:
    filtered = filtered[(filtered["date"] >= date_range[0]) & (filtered["date"] <= date_range[1])]
if segments:
    filtered = filtered[filtered["market_segment"].isin(segments)]
if prop_types:
    filtered = filtered[filtered["property_type"].isin(prop_types)]
if sale_types:
    sale_map = {"1 - New Sale": "1", "2 - Sub Sale": "2", "3 - Resale": "3"}
    sale_codes = [sale_map[s] for s in sale_types]
    filtered = filtered[filtered["type_of_sale"].astype(str).isin(sale_codes)]
filtered = filtered[filtered["latitude"].notna()]
if center_lat and show_tx:
    filtered["distance_m"] = filtered.apply(
        lambda r: haversine(center_lat, center_lon, r["latitude"], r["longitude"]), axis=1
    )
    filtered = filtered[filtered["distance_m"] <= radius_m]

# ── BUILD LAYERS ─────────────────────────────────────────
layers = []

# Demographics
demo_data = []
if show_demo:
    with st.spinner("Loading demographics..."):
        boundaries, _bounds_fetched_at = load_planning_area_boundaries()
        demographics, _demo_fetched_at = load_demographics()
        demo_data = build_planning_area_data(boundaries, demographics)
    layers += build_demographics_layer(demo_data, demo_metric)

# Master Plan
if show_mp:
    if not center_lat:
        st.warning("⚠️ Search a location first to load Master Plan.")
    else:
        with st.spinner("Loading Master Plan 2025..."):
            mp_geojson, _mp_fetched_at = load_masterplan()
        layers += build_masterplan_layer(mp_geojson, center_lat, center_lon, radius_m)

# GLS
if show_gls:
    with st.spinner("Loading GLS sites..."):
        gls_geojson, _gls_fetched_at = load_gls()
    layers += build_gls_layer(gls_geojson)

# Transactions
if show_tx:
    layers += build_transaction_layer(filtered, tx_view)

# Amenities
all_amenity_data = []

if show_amenities and center_lat and onemap_token:

    if show_mrt:
        with st.spinner("Loading MRT stations..."):
            mrt_stations, _mrt_fetched_at = load_mrt_stations()
        nearby_mrt = [
            s for s in mrt_stations
            if haversine(center_lat, center_lon, s["latitude"], s["longitude"]) <= radius_m
        ]
        for s in nearby_mrt:
            s["category"]     = "🚇 Transport (MRT/LRT)"
            s["distance"]     = haversine(center_lat, center_lon, s["latitude"], s["longitude"])
            s["walking_mins"] = round(s["distance"] / 80, 0)
        layers += build_mrt_layer(nearby_mrt)
        all_amenity_data.extend(nearby_mrt)

    if selected_themes:
        items = load_amenities_onemap(
            onemap_token, list(selected_themes.keys()),
            center_lat, center_lon, radius_m
        )
        for item in items:
            item["color"]        = selected_themes.get(item["theme"], [180, 180, 180, 240])
            item["category"]     = item["theme"]
            item["line_label"]   = ""
            item["distance"]     = haversine(center_lat, center_lon, item["latitude"], item["longitude"])
            item["walking_mins"] = round(item["distance"] / 80, 0)
        all_amenity_data.extend(items)
        layers += build_amenity_layer(items)

    if show_malls:
        with st.spinner("Loading malls..."):
            malls = search_onemap_keyword("mall", center_lat, center_lon, radius_m)
        for m in malls:
            m["color"]        = [255, 100, 0, 240]
            m["category"]     = "🛍️ Shopping Malls"
            m["line_label"]   = ""
            m["walking_mins"] = round(m["distance"] / 80, 0)
        all_amenity_data.extend(malls)
        layers += build_amenity_layer(malls)

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
            s["category"]     = "🛒 Supermarkets"
            s["line_label"]   = ""
            s["walking_mins"] = round(s["distance"] / 80, 0)
        all_amenity_data.extend(supermarkets)
        layers += build_amenity_layer(supermarkets)

    if show_schools:
        with st.spinner("Loading schools..."):
            all_schools, _schools_fetched_at = load_schools()
        nearby_schools = [
            s for s in all_schools
            if haversine(center_lat, center_lon, s["latitude"], s["longitude"]) <= radius_m
        ]
        for s in nearby_schools:
            s["color"]        = [0, 153, 0, 240]
            s["category"]     = "🏫 Schools"
            s["line_label"]   = s.get("theme", "")
            s["distance"]     = haversine(center_lat, center_lon, s["latitude"], s["longitude"])
            s["walking_mins"] = round(s["distance"] / 80, 0)
        all_amenity_data.extend(nearby_schools)
        layers += build_amenity_layer(nearby_schools)

    if all_amenity_data:
        st.sidebar.markdown(f"**{len(all_amenity_data):,} amenities found**")

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

if show_tx and not show_gls and not show_mp and not show_amenities and not show_demo:
    active_tooltip = TOOLTIP_TRANSACTIONS
elif show_gls and not show_tx and not show_mp and not show_amenities and not show_demo:
    active_tooltip = TOOLTIP_GLS
elif show_mp and not show_tx and not show_gls and not show_amenities and not show_demo:
    active_tooltip = TOOLTIP_MASTERPLAN
elif show_demo and not show_tx and not show_gls and not show_mp and not show_amenities:
    active_tooltip = TOOLTIP_DEMOGRAPHICS
elif show_amenities and not show_tx and not show_gls and not show_mp and not show_demo:
    active_tooltip = TOOLTIP_AMENITY
else:
    active_tooltip = {
        "html": """
            <div style='font-size:12px;padding:8px;max-width:260px;line-height:1.8;font-family:sans-serif'>
            <b>{name}{project}{location}{lu_desc}{planning_area}</b><br/>
            <span style='color:#666;font-size:11px'>{line_label}{theme}{devt_code}{street}</span>
            </div>
        """,
        "style": {"backgroundColor": "white", "color": "black"}
    }

st.pydeck_chart(pdk.Deck(
    layers=layers,
    initial_view_state=view_state,
    tooltip=active_tooltip,
    map_style=ONEMAP_BASEMAP,
), height=650)

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

# ── DEMOGRAPHICS PANEL ───────────────────────────────────
if show_demo and demo_data:
    st.markdown("---")
    st.markdown("### 🏘️ Demographics")

    # Find closest planning area to search point if available
    if center_lat:
        def get_centroid_coords(x):
            try:
                coords = x["coordinates"]
                flat = coords[0] if isinstance(coords[0][0], list) else coords
                c_lat = sum(c[1] for c in flat) / len(flat)
                c_lon = sum(c[0] for c in flat) / len(flat)
                return c_lat, c_lon
            except:
                return None, None

        closest = None
        min_dist = float("inf")
        for pa in demo_data:
            c_lat, c_lon = get_centroid_coords(pa)
            if c_lat is None:
                continue
            d = haversine(center_lat, center_lon, c_lat, c_lon)
            if d < min_dist:
                min_dist = d
                closest = pa

        if closest:
            st.markdown(f"**Planning Area: {closest['planning_area']}**")
            col1, col2, col3, col4, col5 = st.columns(5)
            col1.metric("Total Population",  closest["total_pop"])
            col2.metric("Pop Density /km²",  closest["pop_density"])
            col3.metric("Young (0-24)",       closest["pct_young"])
            col4.metric("Elderly (65+)",      closest["pct_elderly"])
            col5.metric("% Private Housing",  closest["pct_private"])

    # Full table — always shown
    with st.expander("All Planning Areas" if center_lat else "Planning Area Demographics"):
        demo_df = pd.DataFrame([{
            "Planning Area":   d["planning_area"],
            "Population":      d["total_pop"],
            "Density /km²":    d["pop_density"],
            "% Young (0-24)":  d["pct_young"],
            "% Elderly (65+)": d["pct_elderly"],
            "% HDB":           d["pct_hdb"],
            "% Private":       d["pct_private"],
        } for d in demo_data]).sort_values("Population", ascending=False).reset_index(drop=True)
        st.dataframe(demo_df, use_container_width=True, hide_index=True)
        
# ── AMENITIES TABLE ──────────────────────────────────────
if show_amenities and all_amenity_data:
    st.markdown("---")
    st.markdown("### 📍 Nearby Amenities")

    rows = []
    for a in all_amenity_data:
        dist = a.get("distance", 0)
        rows.append({
            "Name":         a.get("name", ""),
            "Line / Type":  a.get("line_label") or a.get("theme", ""),
            "Category":     a.get("category", a.get("theme", "")),
            "Distance (m)": int(round(dist, 0)),
            "Walk (mins)":  int(round(dist / 80, 0)),
        })

    amenity_df = pd.DataFrame(rows).sort_values(["Category", "Distance (m)"]).reset_index(drop=True)
    for category, group in amenity_df.groupby("Category"):
        with st.expander(f"{category} ({len(group)})"):
            st.dataframe(
                group[["Name", "Line / Type", "Distance (m)", "Walk (mins)"]]
                .reset_index(drop=True),
                use_container_width=True,
                hide_index=True
            )

# ── CHARTS ───────────────────────────────────────────────
if show_tx and len(filtered) > 0:
    st.markdown("---")
    render_charts(filtered)

# ── DATA SOURCES DIALOG ──────────────────────────────────
@st.dialog("Data Sources & Reference", width="large")
def _show_data_sources_dialog(df_tx, csv_mtime, tx_min, tx_max):
    with st.spinner("Preparing downloads..."):
        gls_geojson,  gls_fetched    = load_gls()
        mp_geojson,   mp_fetched     = load_masterplan()
        mrt_stations, mrt_fetched    = load_mrt_stations()
        boundaries,   bounds_fetched = load_planning_area_boundaries()
        demographics, demo_fetched   = load_demographics()
        schools,      sch_fetched    = load_schools()

    demo_pa = build_planning_area_data(boundaries, demographics) if boundaries and demographics else []

    def _fmt(ts):
        return ts.strftime("%d %b %Y, %H:%M") if ts else "—"

    tx_pulled = (
        csv_mtime.strftime("%d %b %Y, %H:%M") if csv_mtime is not None
        else (
            f"{tx_min.strftime('%b %Y')} – {tx_max.strftime('%b %Y')}"
            if pd.notna(tx_min) and pd.notna(tx_max) else "—"
        )
    )

    def _csv(df):
        return df.to_csv(index=False).encode("utf-8")

    def _json(obj):
        return json.dumps(obj).encode("utf-8") if obj else None

    demos_df = pd.DataFrame([{
        "Planning Area":   d["planning_area"],
        "Total Population": d["total_pop"],
        "Density /km²":    d["pop_density"],
        "% Young (0-24)":  d["pct_young"],
        "% Elderly (65+)": d["pct_elderly"],
        "% HDB":           d["pct_hdb"],
        "% Private":       d["pct_private"],
    } for d in demo_pa]) if demo_pa else pd.DataFrame()

    mrt_df = pd.DataFrame([{
        "name":       s["name"],
        "lines":      "/".join(s.get("lines", [])),
        "rail_type":  s.get("rail_type", ""),
        "latitude":   s["latitude"],
        "longitude":  s["longitude"],
    } for s in mrt_stations]) if mrt_stations else pd.DataFrame()

    sch_df = pd.DataFrame([{
        "name":      s["name"],
        "level":     s.get("theme", ""),
        "latitude":  s["latitude"],
        "longitude": s["longitude"],
    } for s in schools]) if schools else pd.DataFrame()

    # dl_key → (bytes, filename, mime, pulled_str)
    _downloads = {
        "ura_transactions": (_csv(df_tx),                   "ura_transactions.csv",      "text/csv",              tx_pulled),
        "gls":              (_json(gls_geojson),             "gls_sites.geojson",         "application/geo+json",  _fmt(gls_fetched)),
        "masterplan":       (_json(mp_geojson),              "masterplan_2025.geojson",   "application/geo+json",  _fmt(mp_fetched)),
        "mrt":              (_csv(mrt_df) if not mrt_df.empty else None,
                                                             "mrt_stations.csv",          "text/csv",              _fmt(mrt_fetched)),
        "boundaries":       (_json(boundaries),              "planning_areas.geojson",    "application/geo+json",  _fmt(bounds_fetched)),
        "demographics":     (_csv(demos_df) if not demos_df.empty else None,
                                                             "demographics.csv",          "text/csv",              _fmt(demo_fetched)),
        "schools":          (_csv(sch_df) if not sch_df.empty else None,
                                                             "schools.csv",               "text/csv",              _fmt(sch_fetched)),
    }

    for row in DATA_SOURCES:
        host_updated = tx_pulled if row["updated"] is None else row["updated"]
        dl_key       = row.get("dl_key")
        dl_bytes, dl_file, dl_mime, pulled_str = _downloads.get(dl_key, (None, None, None, "—"))

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
                    key=f"dl_{dl_key}_{row['layer']}",
                )
            elif dl_key is None:
                st.caption("Live — varies by search")
            else:
                st.caption("Not yet loaded")
        st.divider()

# ── SIDEBAR: FOOTER ──────────────────────────────────────
st.sidebar.markdown("---")
if st.sidebar.button("📋 Data Sources & Reference"):
    _show_data_sources_dialog(
        df_tx=df_tx,
        csv_mtime=_csv_mtime,
        tx_min=_tx_min,
        tx_max=_tx_max,
    )

st.sidebar.caption("Property Hub · URA · OneMap · data.gov.sg")
