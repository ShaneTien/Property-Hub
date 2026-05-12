import streamlit as st
import pandas as pd
import requests
import pydeck as pdk
from pyproj import Transformer
import time

st.set_page_config(page_title="Transactions", page_icon="📊", layout="wide")
st.title("📊 URA Private Residential Transactions")

# ── DATA LOADING ─────────────────────────────────────────
@st.cache_data(ttl=43200)  # cache for 12 hours
def load_data(access_key):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }

    # Get token
    token_url = "https://eservice.ura.gov.sg/uraDataService/insertNewToken/v1"
    token = requests.get(token_url, headers={**headers, "AccessKey": access_key}).json()["Result"]

    # Pull all 4 batches
    rows = []
    transformer = Transformer.from_crs("EPSG:3414", "EPSG:4326", always_xy=True)

    for batch in range(1, 5):
        url = f"https://eservice.ura.gov.sg/uraDataService/invokeUraDS/v1?service=PMI_Resi_Transaction&batch={batch}"
        data = requests.get(url, headers={**headers, "AccessKey": access_key, "Token": token}).json().get("Result", [])

        for project in data:
            # Convert coordinates
            lat, lon = None, None
            try:
                x, y = float(project.get("x")), float(project.get("y"))
                lon, lat = transformer.transform(x, y)
                lat, lon = round(lat, 6), round(lon, 6)
            except:
                pass

            for t in project.get("transaction", []):
                rows.append({
                    "project":        project.get("project"),
                    "street":         project.get("street"),
                    "market_segment": project.get("marketSegment"),
                    "latitude":       lat,
                    "longitude":      lon,
                    "contract_date":  t.get("contractDate"),
                    "area_sqm":       pd.to_numeric(t.get("area"), errors="coerce"),
                    "price_sgd":      pd.to_numeric(t.get("price"), errors="coerce"),
                    "property_type":  t.get("propertyType"),
                    "tenure":         t.get("tenure"),
                    "floor_range":    t.get("floorRange"),
                    "type_of_sale":   t.get("typeOfSale"),
                    "district":       t.get("district"),
                })
        time.sleep(0.5)

    df = pd.DataFrame(rows)
    df["area_sqft"] = (df["area_sqm"] * 10.7639).round(0)
    df["psf"]       = (df["price_sgd"] / df["area_sqft"]).round(0)

    # Parse contract date (format: mmyy e.g. 0123 = Jan 2023)
    df["month"] = df["contract_date"].str[:2]
    df["year"]  = "20" + df["contract_date"].str[2:]
    df["date"]  = pd.to_datetime(df["year"] + "-" + df["month"], format="%Y-%m", errors="coerce")

    return df

# ── ACCESS KEY ───────────────────────────────────────────
try:
    access_key = st.secrets["URA_ACCESS_KEY"]
except:
    access_key = st.sidebar.text_input("Enter URA Access Key", type="password")
    if not access_key:
        st.warning("Please enter your URA Access Key in the sidebar to load data.")
        st.stop()

# ── LOAD DATA ────────────────────────────────────────────
with st.spinner("Loading URA transaction data..."):
    df = load_data(access_key)

st.sidebar.success(f"✅ {len(df):,} transactions loaded")

# ── FILTERS ──────────────────────────────────────────────
st.sidebar.markdown("## Filters")

# Date range
min_date = df["date"].min()
max_date = df["date"].max()
date_range = st.sidebar.slider(
    "Contract Date",
    min_value=min_date.to_pydatetime(),
    max_value=max_date.to_pydatetime(),
    value=(min_date.to_pydatetime(), max_date.to_pydatetime()),
    format="MMM YYYY"
)

# Market segment
segments = st.sidebar.multiselect(
    "Market Segment",
    options=["CCR", "RCR", "OCR"],
    default=[]
)

# Property type
prop_types = sorted(df["property_type"].dropna().unique())
selected_types = st.sidebar.multiselect(
    "Property Type",
    options=prop_types,
    default=[]
)

# District
districts = sorted(df["district"].dropna().unique())
selected_districts = st.sidebar.multiselect(
    "District",
    options=districts,
    default=[]
)

# Tenure
tenures = st.sidebar.multiselect(
    "Tenure",
    options=["Freehold", "999 yrs", "99 yrs"],
    default=[]
)

# Type of sale
sale_types = st.sidebar.multiselect(
    "Type of Sale",
    options=["1 - New Sale", "2 - Sub Sale", "3 - Resale"],
    default=[]
)

# PSF range
psf_min, psf_max = int(df["psf"].min()), int(df["psf"].max())
psf_range = st.sidebar.slider("PSF Range (S$)", psf_min, psf_max, (psf_min, psf_max))

# ── APPLY FILTERS ────────────────────────────────────────
filtered = df.copy()

filtered = filtered[(filtered["date"] >= date_range[0]) & (filtered["date"] <= date_range[1])]
if segments:
    filtered = filtered[filtered["market_segment"].isin(segments)]
if selected_types:
    filtered = filtered[filtered["property_type"].isin(selected_types)]
if selected_districts:
    filtered = filtered[filtered["district"].isin(selected_districts)]
if tenures:
    tenure_filter = "|".join(tenures)
    filtered = filtered[filtered["tenure"].str.contains(tenure_filter, na=False)]
if sale_types:
    sale_map = {"1 - New Sale": "1", "2 - Sub Sale": "2", "3 - Resale": "3"}
    selected_codes = [sale_map[s] for s in sale_types]
    filtered = filtered[filtered["type_of_sale"].isin(selected_codes)]
filtered = filtered[(filtered["psf"] >= psf_range[0]) & (filtered["psf"] <= psf_range[1])]
filtered = filtered[filtered["latitude"].notna()]

st.sidebar.markdown(f"**Showing {len(filtered):,} transactions**")

# ── SUMMARY STATS ────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)
col1.metric("Transactions", f"{len(filtered):,}")
col2.metric("Median PSF", f"S${filtered['psf'].median():,.0f}")
col3.metric("Median Price", f"S${filtered['price_sgd'].median()/1e6:.2f}M")
col4.metric("Avg Area", f"{filtered['area_sqft'].mean():,.0f} sqft")

st.markdown("---")

# ── PSF COLOUR SCALE ─────────────────────────────────────
def psf_to_color(psf, min_psf, max_psf):
    ratio = min(max((psf - min_psf) / (max_psf - min_psf + 1), 0), 1)
    r = int(255 * ratio)
    g = int(255 * (1 - ratio))
    return [r, g, 50, 180]

map_df = filtered[["latitude", "longitude", "psf", "project", "price_sgd", "area_sqft", "floor_range", "tenure", "contract_date"]].copy()
min_psf = map_df["psf"].min()
max_psf = map_df["psf"].max()
map_df["color"] = map_df["psf"].apply(lambda x: psf_to_color(x, min_psf, max_psf))

# ── MAP ──────────────────────────────────────────────────
layer = pdk.Layer(
    "ScatterplotLayer",
    data=map_df,
    get_position=["longitude", "latitude"],
    get_fill_color="color",
    get_radius=50,
    pickable=True,
    opacity=0.8,
)

view_state = pdk.ViewState(
    latitude=1.3521,
    longitude=103.8198,
    zoom=11,
    pitch=0,
)

tooltip = {
    "html": "<b>{project}</b><br/>PSF: S${psf}<br/>Price: S${price_sgd}<br/>Area: {area_sqft} sqft<br/>Floor: {floor_range}<br/>Tenure: {tenure}",
    "style": {"backgroundColor": "white", "color": "black", "fontSize": "12px", "padding": "10px"}
}

st.pydeck_chart(pdk.Deck(
    layers=[layer],
    initial_view_state=view_state,
    tooltip=tooltip,
    map_style="https://www.onemap.gov.sg/maps/json/raster/mbstyle/Default.json"
))

# ── PSF LEGEND ───────────────────────────────────────────
st.markdown(f"🟢 Low PSF (S${min_psf:,.0f}) &nbsp;&nbsp; 🔴 High PSF (S${max_psf:,.0f})")

# ── DATA TABLE ───────────────────────────────────────────
with st.expander("View transaction data"):
    st.dataframe(
        filtered[["project","street","district","market_segment","property_type",
                  "tenure","floor_range","area_sqft","psf","price_sgd","type_of_sale","date"]]
        .sort_values("date", ascending=False)
        .reset_index(drop=True),
        use_container_width=True
    )
