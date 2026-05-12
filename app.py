import streamlit as st
import requests
import pydeck as pdk
import pandas as pd
import time
import math
from pyproj import Transformer

st.set_page_config(page_title="Property Hub", page_icon="🏙️", layout="wide")
st.title("🏙️ Property Hub")

# ── CONSTANTS ────────────────────────────────────────────
TRANSFORMER = Transformer.from_crs("EPSG:3414", "EPSG:4326", always_xy=True)
ONEMAP_BASEMAP = "https://www.onemap.gov.sg/maps/json/raster/mbstyle/Default.json"

LAND_USE_COLORS = {
    # Residential
    "RESIDENTIAL":                      [255, 218, 185, 180],  # peach/beige
    "RESIDENTIAL WITH COMMERCIAL AT 1ST STOREY": [255, 200, 150, 180],
    # Commercial
    "COMMERCIAL":                       [255, 0, 0, 180],      # red
    "COMMERCIAL & RESIDENTIAL":         [255, 160, 122, 180],  # light salmon
    # Hotel
    "HOTEL":                            [255, 105, 180, 180],  # hot pink
    # White
    "WHITE":                            [255, 255, 255, 200],  # white
    # Business/Industrial
    "BUSINESS 1":                       [153, 153, 255, 180],  # light purple
    "BUSINESS 1 - WHITE":               [180, 153, 255, 180],
    "BUSINESS 2":                       [102, 102, 204, 180],  # medium purple
    "BUSINESS 2 - WHITE":               [130, 102, 204, 180],
    "BUSINESS PARK":                    [204, 153, 255, 180],  # lavender
    "BUSINESS PARK - WHITE":            [220, 180, 255, 180],
    # Open space & greenery
    "OPEN SPACE":                       [0, 180, 0, 180],      # green
    "PARK":                             [0, 153, 0, 180],      # dark green
    "NATURE RESERVE":                   [0, 102, 0, 180],      # very dark green
    "BEACH AREA":                       [135, 206, 235, 180],  # sky blue
    "WATERBODY":                        [0, 150, 255, 180],    # blue
    # Transport
    "TRANSPORT":                        [200, 200, 200, 180],  # grey
    "ROAD":                             [220, 220, 220, 180],  # light grey
    "MASS RAPID TRANSIT":               [160, 160, 160, 180],
    # Civic & institutions
    "CIVIC & COMMUNITY":                [0, 220, 220, 180],    # cyan
    "EDUCATIONAL INSTITUTION":          [0, 191, 255, 180],    # deep sky blue
    "HEALTH & MEDICAL CARE":            [255, 0, 128, 180],    # magenta
    "PLACE OF WORSHIP":                 [210, 180, 140, 180],  # tan
    "COMMUNITY INSTITUTION":            [100, 220, 220, 180],
    # Utilities & others
    "UTILITY":                          [255, 255, 0, 180],    # yellow
    "SPECIAL USE":                      [200, 180, 160, 180],
    "RESERVE SITE":                     [211, 211, 211, 180],  # light grey
    "CEMETERY":                         [180, 180, 180, 180],
    "PORT / AIRPORT":                   [160, 160, 160, 180],
    "AGRICULTURE":                      [144, 238, 144, 180],  # light green
}
DEFAULT_COLOR = [220, 220, 220, 120]

# ── DATA LOADERS ─────────────────────────────────────────
@st.cache_data(ttl=43200)
def load_transactions(access_key):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    token = requests.get(
        "https://eservice.ura.gov.sg/uraDataService/insertNewToken/v1",
        headers={**headers, "AccessKey": access_key}
    ).json()["Result"]

    rows = []
    for batch in range(1, 5):
        url = f"https://eservice.ura.gov.sg/uraDataService/invokeUraDS/v1?service=PMI_Resi_Transaction&batch={batch}"
        data = requests.get(url, headers={**headers, "AccessKey": access_key, "Token": token}).json().get("Result", [])
        for project in data:
            lat, lon = None, None
            try:
                x, y = float(project.get("x")), float(project.get("y"))
                lon, lat = TRANSFORMER.transform(x, y)
                lat, lon = round(lat, 6), round(lon, 6)
            except:
                pass
            for t in project.get("transaction", []):
                price = pd.to_numeric(t.get("price"), errors="coerce")
                area_sqm = pd.to_numeric(t.get("area"), errors="coerce")
                area_sqft = round(area_sqm * 10.7639, 0) if pd.notna(area_sqm) else None
                psf = round(price / area_sqft, 0) if area_sqft and area_sqft > 0 else None
                rows.append({
                    "project":        project.get("project"),
                    "street":         project.get("street"),
                    "market_segment": project.get("marketSegment"),
                    "latitude":       lat,
                    "longitude":      lon,
                    "contract_date":  t.get("contractDate"),
                    "area_sqm":       area_sqm,
                    "area_sqft":      area_sqft,
                    "price_sgd":      price,
                    "psf":            psf,
                    "property_type":  t.get("propertyType"),
                    "tenure":         t.get("tenure"),
                    "floor_range":    t.get("floorRange"),
                    "type_of_sale":   t.get("typeOfSale"),
                    "district":       t.get("district"),
                })
        time.sleep(0.5)

    df = pd.DataFrame(rows)
    df["month"] = df["contract_date"].str[:2]
    df["year"]  = "20" + df["contract_date"].str[2:]
    df["date"]  = pd.to_datetime(df["year"] + "-" + df["month"], format="%Y-%m", errors="coerce")
    return df

@st.cache_data(ttl=86400)
def load_gls():
    dataset_id = "d_0e2b42f98535686282031a42c9c7b05a"
    poll_url = f"https://api-open.data.gov.sg/v1/public/api/datasets/{dataset_id}/poll-download"
    for _ in range(10):
        r = requests.get(poll_url).json()
        if r.get("code") == 0:
            url = r.get("data", {}).get("url")
            if url:
                return requests.get(url).json()
        time.sleep(2)
    return None

@st.cache_data(ttl=86400)
def load_masterplan():
    dataset_id = "d_a8c3546b26712e35021f3a681d0353ae"
    poll_url = f"https://api-open.data.gov.sg/v1/public/api/datasets/{dataset_id}/poll-download"
    for _ in range(15):
        r = requests.get(poll_url).json()
        if r.get("code") == 0:
            url = r.get("data", {}).get("url")
            if url:
                return requests.get(url).json()
        time.sleep(2)
    return None

def geocode_address(address):
    url = f"https://www.onemap.gov.sg/api/common/elastic/search?searchVal={address}&returnGeom=Y&getAddrDetails=Y&pageNum=1"
    try:
        r = requests.get(url, timeout=10).json()
        if r.get("found", 0) > 0:
            result = r["results"][0]
            return float(result["LATITUDE"]), float(result["LONGITUDE"]), result.get("ADDRESS", address)
    except:
        pass
    return None, None, None

def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

def make_circle(lat, lon, radius_m, n=64):
    coords = []
    for i in range(n + 1):
        angle = 2 * math.pi * i / n
        dlat = (radius_m / 111320) * math.cos(angle)
        dlon = (radius_m / (111320 * math.cos(math.radians(lat)))) * math.sin(angle)
        coords.append([lon + dlon, lat + dlat])
    return coords

def psf_to_color(psf, min_psf, max_psf):
    ratio = min(max((psf - min_psf) / (max_psf - min_psf + 1), 0), 1)
    return [int(255 * ratio), int(255 * (1 - ratio)), 50, 180]

def parse_date(d):
    if not d or str(d) == "0":
        return "N/A"
    try:
        from datetime import datetime
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

# ── ACCESS KEY ───────────────────────────────────────────
try:
    access_key = st.secrets["URA_ACCESS_KEY"]
except:
    access_key = st.sidebar.text_input("URA Access Key", type="password")
    if not access_key:
        st.warning("Enter your URA Access Key in the sidebar.")
        st.stop()

# ── LOAD DATA ────────────────────────────────────────────
with st.spinner("Loading data..."):
    df_tx = load_transactions(access_key)
st.sidebar.success(f"✅ {len(df_tx):,} transactions loaded")

# ── SIDEBAR ──────────────────────────────────────────────
st.sidebar.markdown("---")
st.sidebar.markdown("## 🔍 Location Search")
search_query = st.sidebar.text_input("Search address or project name", placeholder="e.g. Orchard Road, Marina Bay")
radius_m = st.sidebar.slider("Search radius (m)", 250, 2000, 500, step=250)

center_lat, center_lon, resolved_address = None, None, None
if search_query:
    center_lat, center_lon, resolved_address = geocode_address(search_query)
    if center_lat:
        st.sidebar.success(f"📍 {resolved_address}")
    else:
        st.sidebar.error("Address not found. Try a different search.")

st.sidebar.markdown("---")
st.sidebar.markdown("## 🗂️ Layers")
show_tx      = st.sidebar.checkbox("Transactions", value=False)
tx_view      = st.sidebar.radio("Transaction view", ["Points", "Heatmap"], horizontal=True) if show_tx else "Points"
show_gls     = st.sidebar.checkbox("GLS Sites", value=False)
show_mp      = st.sidebar.checkbox("Master Plan 2025", value=False)

st.sidebar.markdown("---")
st.sidebar.markdown("## 🔧 Filters")
segments      = st.sidebar.multiselect("Market Segment", ["CCR", "RCR", "OCR"], default=[])
prop_types    = st.sidebar.multiselect("Property Type", sorted(df_tx["property_type"].dropna().unique()), default=[])
sale_types    = st.sidebar.multiselect("Type of Sale", ["1 - New Sale", "2 - Sub Sale", "3 - Resale"], default=[])
min_date      = df_tx["date"].min().to_pydatetime()
max_date      = df_tx["date"].max().to_pydatetime()
date_range    = st.sidebar.slider("Contract Date", min_value=min_date, max_value=max_date, value=(min_date, max_date), format="MMM YYYY")
psf_min, psf_max = int(df_tx["psf"].min()), int(df_tx["psf"].max())
psf_range     = st.sidebar.slider("PSF (S$)", psf_min, psf_max, (psf_min, psf_max))

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

# Radius filter
if center_lat:
    filtered = filtered[filtered["latitude"].notna()]
    filtered["distance_m"] = filtered.apply(
        lambda r: haversine(center_lat, center_lon, r["latitude"], r["longitude"]), axis=1
    )
    filtered = filtered[filtered["distance_m"] <= radius_m]
else:
    filtered = filtered[filtered["latitude"].notna()]

st.sidebar.markdown(f"**{len(filtered):,} transactions**")

# ── SUMMARY STATS ────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)
col1.metric("Transactions", f"{len(filtered):,}")
col2.metric("Median PSF", f"S${filtered['psf'].median():,.0f}" if len(filtered) else "—")
col3.metric("Median Price", f"S${filtered['price_sgd'].median()/1e6:.2f}M" if len(filtered) else "—")
col4.metric("Avg Area", f"{filtered['area_sqft'].mean():,.0f} sqft" if len(filtered) else "—")

st.markdown("---")

# ── BUILD LAYERS ─────────────────────────────────────────
layers = []

# Master Plan layer
if show_mp:
    with st.spinner("Loading Master Plan 2025..."):
        mp_geojson = load_masterplan()
    if mp_geojson:
        mp_data = []
        for f in mp_geojson.get("features", []):
            lu = f.get("properties", {}).get("LU_DESC", "")
            gpr = f.get("properties", {}).get("GPR", "")
            color = LAND_USE_COLORS.get(lu.upper(), DEFAULT_COLOR)
            coords = f["geometry"]["coordinates"]
            
            # If location searched, only include polygons near the search point
            if center_lat:
                try:
                    flat_coords = coords[0] if isinstance(coords[0][0], list) else coords
                    lons = [c[0] for c in flat_coords]
                    lats = [c[1] for c in flat_coords]
                    c_lon = sum(lons) / len(lons)
                    c_lat = sum(lats) / len(lats)
                    dist = haversine(center_lat, center_lon, c_lat, c_lon)
                    if dist > radius_m * 2:
                        continue
                except:
                    continue

            mp_data.append({
                "coordinates": coords,
                "lu_desc": lu,
                "gpr": gpr,
                "color": color,
            })
        
        if not center_lat:
            st.warning("⚠️ Master Plan layer is large — search a location first to load it for that area only.")
        else:
            layers.append(pdk.Layer(
                "PolygonLayer",
                data=mp_data,
                get_polygon="coordinates",
                get_fill_color="color",
                get_line_color=[150, 150, 150, 80],
                get_line_width=1,
                pickable=True,
                stroked=True,
                filled=True,
            ))
        layers.append(pdk.Layer(
            "PolygonLayer",
            data=mp_data,
            get_polygon="coordinates",
            get_fill_color="color",
            get_line_color=[150, 150, 150, 80],
            get_line_width=1,
            pickable=True,
            stroked=True,
            filled=True,
        ))

# GLS layer
if show_gls:
    with st.spinner("Loading GLS sites..."):
        gls_geojson = load_gls()
    if gls_geojson:
        gls_polygons, gls_dots = [], []
        for f in gls_geojson.get("features", []):
            props = f.get("properties", {})
            coords = f["geometry"]["coordinates"]
            lon, lat = get_centroid(coords)
            item = {
                "coordinates": coords,
                "location":    props.get("LOCATION", ""),
                "devt_code":   props.get("DEVT_CODE", ""),
                "lease_yr":    props.get("LEASE_YR", ""),
                "gpr":         props.get("GPR", ""),
                "housing_un":  props.get("HOUSING_UN", ""),
                "no_of_bids":  props.get("NO_OF_BIDS", ""),
                "date_award":  parse_date(props.get("DATE_AWARD")),
            }
            gls_polygons.append(item)
            if lat and lon:
                gls_dots.append({**item, "latitude": lat, "longitude": lon})

        layers.append(pdk.Layer(
            "PolygonLayer",
            data=gls_polygons,
            get_polygon="coordinates",
            get_fill_color=[255, 140, 0, 100],
            get_line_color=[255, 100, 0, 200],
            get_line_width=2,
            pickable=True,
            stroked=True,
            filled=True,
        ))
        layers.append(pdk.Layer(
            "ScatterplotLayer",
            data=gls_dots,
            get_position=["longitude", "latitude"],
            get_fill_color=[255, 80, 0, 220],
            get_radius=40,
            pickable=True,
        ))

# Transaction layer
if show_tx and len(filtered) > 0:
    if tx_view == "Heatmap":
        layers.append(pdk.Layer(
            "HeatmapLayer",
            data=filtered[["latitude", "longitude", "psf"]],
            get_position=["longitude", "latitude"],
            get_weight="psf",
            radiusPixels=40,
            opacity=0.8,
        ))
    else:
        min_psf = filtered["psf"].min()
        max_psf = filtered["psf"].max()
        tx_map = filtered.copy()
        tx_map["color"] = tx_map["psf"].apply(lambda x: psf_to_color(x, min_psf, max_psf))
        layers.append(pdk.Layer(
            "ScatterplotLayer",
            data=tx_map,
            get_position=["longitude", "latitude"],
            get_fill_color="color",
            get_radius=50,
            pickable=True,
            opacity=0.8,
        ))

# Radius ring
if center_lat:
    ring_coords = make_circle(center_lat, center_lon, radius_m)
    layers.append(pdk.Layer(
        "PolygonLayer",
        data=[{"coordinates": [ring_coords]}],
        get_polygon="coordinates",
        get_fill_color=[100, 150, 255, 30],
        get_line_color=[100, 150, 255, 200],
        get_line_width=3,
        stroked=True,
        filled=True,
    ))
    layers.append(pdk.Layer(
        "ScatterplotLayer",
        data=[{"lat": center_lat, "lon": center_lon}],
        get_position=["lon", "lat"],
        get_fill_color=[50, 100, 255, 255],
        get_radius=30,
    ))

# ── VIEW STATE ───────────────────────────────────────────
view_state = pdk.ViewState(
    latitude=center_lat if center_lat else 1.3521,
    longitude=center_lon if center_lon else 103.8198,
    zoom=14 if center_lat else 11,
    pitch=0,
)

# ── TOOLTIP ──────────────────────────────────────────────
tooltip = {
    "html": """
        <div style='font-size:12px;padding:8px;'>
        <b>{project}{location}{lu_desc}</b><br/>
        {devt_code}
        PSF: S${psf} &nbsp;|&nbsp; Price: S${price_sgd}<br/>
        Area: {area_sqft} sqft &nbsp;|&nbsp; Floor: {floor_range}<br/>
        Tenure: {tenure}{lease_yr}<br/>
        GPR: {gpr}<br/>
        Awarded: {date_award}
        </div>
    """,
    "style": {"backgroundColor": "white", "color": "black"}
}

# ── MAP ──────────────────────────────────────────────────
if layers:
    st.pydeck_chart(pdk.Deck(
        layers=layers,
        initial_view_state=view_state,
        tooltip=tooltip,
        map_style=ONEMAP_BASEMAP,
    ))
    if show_tx and tx_view == "Points":
        st.markdown(f"🟢 Low PSF &nbsp;&nbsp; 🔴 High PSF")
else:
    st.pydeck_chart(pdk.Deck(
        layers=[],
        initial_view_state=view_state,
        map_style=ONEMAP_BASEMAP,
    ))
    st.info("👈 Toggle layers in the sidebar to display data on the map.")

# ── CHARTS ───────────────────────────────────────────────
if show_tx and len(filtered) > 0:
    st.markdown("---")
    st.markdown("### 📊 Transaction Analysis")

    tab1, tab2, tab3, tab4 = st.tabs(["PSF Trend", "Volume", "PSF Distribution", "By Property Type"])

    with tab1:
        trend = filtered.groupby("date")["psf"].median().reset_index()
        trend.columns = ["Date", "Median PSF"]
        st.line_chart(trend.set_index("Date"))

    with tab2:
        vol = filtered.groupby("date").size().reset_index(name="Transactions")
        st.bar_chart(vol.set_index("date"))

    with tab3:
        import numpy as np
        psf_vals = filtered["psf"].dropna()
        hist, edges = np.histogram(psf_vals, bins=40)
        hist_df = pd.DataFrame({"PSF": edges[:-1], "Count": hist})
        st.bar_chart(hist_df.set_index("PSF"))

    with tab4:
        by_type = filtered.groupby("property_type")["psf"].median().sort_values(ascending=False).reset_index()
        by_type.columns = ["Property Type", "Median PSF"]
        st.bar_chart(by_type.set_index("Property Type"))

    st.markdown("---")
    with st.expander("View transaction data"):
        st.dataframe(
            filtered[["project", "street", "district", "market_segment", "property_type",
                      "tenure", "floor_range", "area_sqft", "psf", "price_sgd", "type_of_sale", "date"]]
            .sort_values("date", ascending=False)
            .reset_index(drop=True),
            use_container_width=True
        )

st.markdown("---")
st.caption("Data: URA Data Service API · Master Plan 2025 · data.gov.sg · Updated Tue & Fri")
