import streamlit as st
import requests
import pydeck as pdk
import pandas as pd
import time
from datetime import datetime

st.set_page_config(page_title="GLS Sites", page_icon="🏗️", layout="wide")
st.title("🏗️ Government Land Sales")

# ── DATA LOADING ─────────────────────────────────────────
@st.cache_data(ttl=86400)
def load_gls_sites():
    dataset_id = "d_0e2b42f98535686282031a42c9c7b05a"
    poll_url = f"https://api-open.data.gov.sg/v1/public/api/datasets/{dataset_id}/poll-download"

    for attempt in range(10):
        r = requests.get(poll_url)
        data = r.json()
        if data.get("code") == 0:
            download_url = data.get("data", {}).get("url")
            if download_url:
                geojson = requests.get(download_url).json()
                return geojson
        time.sleep(2)

    raise Exception("Could not download GLS data after retries")

def parse_date(d):
    if not d or d == "0":
        return None
    try:
        return datetime.strptime(str(d), "%Y%m%d").strftime("%d %b %Y")
    except:
        return str(d)

def get_centroid(coordinates):
    try:
        coords = coordinates[0]
        lons = [c[0] for c in coords]
        lats = [c[1] for c in coords]
        return sum(lons)/len(lons), sum(lats)/len(lats)
    except:
        return None, None

# ── LOAD DATA ────────────────────────────────────────────
with st.spinner("Loading GLS site data..."):
    try:
        geojson = load_gls_sites()
    except Exception as e:
        st.error(f"Error loading data: {e}")
        st.stop()

features = geojson.get("features", [])
st.sidebar.success(f"✅ {len(features):,} GLS sites loaded")

# ── PARSE FEATURES ───────────────────────────────────────
sites = []
for f in features:
    props = f.get("properties", {})
    geom  = f.get("geometry", {})
    coords = geom.get("coordinates", [])
    lon, lat = get_centroid(coords)

    date_award  = parse_date(props.get("DATE_AWARD"))
    date_launch = parse_date(props.get("DATE_LNCH"))
    award_year  = None
    if props.get("DATE_AWARD") and str(props.get("DATE_AWARD")) != "0":
        try:
            award_year = int(str(props["DATE_AWARD"])[:4])
        except:
            pass

    sites.append({
        "location":   props.get("LOCATION", ""),
        "devt_code":  props.get("DEVT_CODE", ""),
        "devt_allow": props.get("DEVT_ALLOW", ""),
        "lease_yr":   str(props.get("LEASE_YR", "")),
        "gpr":        props.get("GPR"),
        "gfa":        props.get("GFA"),
        "sa_sqm":     props.get("SA_SQM"),
        "housing_un": props.get("HOUSING_UN"),
        "no_of_bids": props.get("NO_OF_BIDS"),
        "date_launch": date_launch,
        "date_award":  date_award,
        "award_year":  award_year,
        "pln_area":   props.get("PLN_AREA_N", ""),
        "latitude":   lat,
        "longitude":  lon,
        "coordinates": coords,
    })

df = pd.DataFrame(sites)

# ── FILTERS ──────────────────────────────────────────────
st.sidebar.markdown("## Filters")

devt_codes = sorted(df["devt_code"].dropna().unique())
selected_codes = st.sidebar.multiselect("Development Type", devt_codes, default=[])

year_min = int(df["award_year"].min()) if df["award_year"].notna().any() else 1967
year_max = int(df["award_year"].max()) if df["award_year"].notna().any() else 2025
year_range = st.sidebar.slider("Award Year", year_min, year_max, (2010, year_max))

planning_areas = sorted(df["pln_area"].dropna().unique())
selected_areas = st.sidebar.multiselect("Planning Area", planning_areas, default=[])

lease_options = st.sidebar.multiselect("Tenure", ["99", "999", "0"], default=[])

# ── APPLY FILTERS ────────────────────────────────────────
filtered = df.copy()
if selected_codes:
    filtered = filtered[filtered["devt_code"].isin(selected_codes)]
if selected_areas:
    filtered = filtered[filtered["pln_area"].isin(selected_areas)]
if lease_options:
    filtered = filtered[filtered["lease_yr"].isin(lease_options)]
filtered = filtered[
    (filtered["award_year"].isna()) |
    ((filtered["award_year"] >= year_range[0]) & (filtered["award_year"] <= year_range[1]))
]

st.sidebar.markdown(f"**Showing {len(filtered):,} sites**")

# ── SUMMARY STATS ────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)
col1.metric("GLS Sites", f"{len(filtered):,}")
col2.metric("Total Housing Units", f"{filtered['housing_un'].sum():,.0f}")
col3.metric("Avg GPR", f"{filtered['gpr'].mean():.1f}" if filtered["gpr"].notna().any() else "N/A")
col4.metric("Avg Bids", f"{filtered['no_of_bids'].mean():.1f}" if filtered["no_of_bids"].notna().any() else "N/A")

st.markdown("---")

# ── MAP ──────────────────────────────────────────────────
polygon_data = []
for _, row in filtered.iterrows():
    if row["coordinates"]:
        polygon_data.append({
            "coordinates": row["coordinates"],
            "location":    row["location"],
            "devt_code":   row["devt_code"],
            "lease_yr":    row["lease_yr"],
            "gpr":         row["gpr"],
            "housing_un":  row["housing_un"],
            "date_award":  row["date_award"],
            "no_of_bids":  row["no_of_bids"],
        })

polygon_layer = pdk.Layer(
    "PolygonLayer",
    data=polygon_data,
    get_polygon="coordinates",
    get_fill_color=[255, 140, 0, 100],
    get_line_color=[255, 100, 0, 200],
    get_line_width=2,
    pickable=True,
    stroked=True,
    filled=True,
)

dot_df = filtered[filtered["latitude"].notna()].copy()
dot_layer = pdk.Layer(
    "ScatterplotLayer",
    data=dot_df,
    get_position=["longitude", "latitude"],
    get_fill_color=[255, 80, 0, 220],
    get_radius=40,
    pickable=True,
)

view_state = pdk.ViewState(
    latitude=1.3521,
    longitude=103.8198,
    zoom=11,
    pitch=0,
)

tooltip = {
    "html": "<b>{location}</b><br/>Type: {devt_code}<br/>Tenure: {lease_yr} yrs<br/>GPR: {gpr}<br/>Units: {housing_un}<br/>Bids: {no_of_bids}<br/>Awarded: {date_award}",
    "style": {"backgroundColor": "white", "color": "black", "fontSize": "12px", "padding": "10px"}
}

st.pydeck_chart(pdk.Deck(
    layers=[polygon_layer, dot_layer],
    initial_view_state=view_state,
    tooltip=tooltip,
    map_style="https://www.onemap.gov.sg/maps/json/raster/mbstyle/Default.json"
))

# ── DATA TABLE ───────────────────────────────────────────
with st.expander("View GLS site data"):
    st.dataframe(
        filtered[["location", "pln_area", "devt_code", "lease_yr", "gpr", "gfa",
                  "sa_sqm", "housing_un", "no_of_bids", "date_launch", "date_award"]]
        .sort_values("date_award", ascending=False)
        .reset_index(drop=True),
        use_container_width=True
    )
