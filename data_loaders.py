import streamlit as st
import requests
import pandas as pd
import time
from datetime import datetime
from pyproj import Transformer

TRANSFORMER = Transformer.from_crs("EPSG:3414", "EPSG:4326", always_xy=True)


@st.cache_data(ttl=43200)
def load_transactions(access_key=None):
    """Load from cached CSV in repo. Falls back to API if CSV missing."""
    import os
    fetched_at = datetime.now()
    csv_path = os.path.join(os.path.dirname(__file__), "data", "ura_transactions.csv")
    if os.path.exists(csv_path):
        print("Loading from cached CSV...")
        df = pd.read_csv(csv_path)
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        return df, fetched_at
    print("CSV not found, loading from API...")
    df = _load_transactions_from_api(access_key)
    return df, fetched_at


@st.cache_data(ttl=43200)
def _load_transactions_from_api(access_key):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    token = requests.get(
        "https://eservice.ura.gov.sg/uraDataService/insertNewToken/v1",
        headers={**headers, "AccessKey": access_key}
    ).json()["Result"]

    rows = []
    for batch in range(1, 5):
        url  = f"https://eservice.ura.gov.sg/uraDataService/invokeUraDS/v1?service=PMI_Resi_Transaction&batch={batch}"
        data = requests.get(
            url, headers={**headers, "AccessKey": access_key, "Token": token}
        ).json().get("Result", [])

        for project in data:
            lat, lon = None, None
            try:
                x, y     = float(project.get("x")), float(project.get("y"))
                lon, lat = TRANSFORMER.transform(x, y)
                lat, lon = round(lat, 6), round(lon, 6)
            except:
                pass

            for t in project.get("transaction", []):
                price     = pd.to_numeric(t.get("price"), errors="coerce")
                area_sqm  = pd.to_numeric(t.get("area"),  errors="coerce")
                area_sqft = round(area_sqm * 10.7639, 0) if pd.notna(area_sqm) else None
                psf       = round(price / area_sqft, 0) if area_sqft and area_sqft > 0 else None
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

    # Geocode missing projects
    missing = df[df["latitude"].isna()]["project"].dropna().unique()
    geocoded = {}
    for project in missing:
        try:
            url = (
                f"https://www.onemap.gov.sg/api/common/elastic/search"
                f"?searchVal={requests.utils.quote(project)}&returnGeom=Y&getAddrDetails=Y&pageNum=1"
            )
            r = requests.get(url, timeout=5).json()
            if r.get("found", 0) > 0:
                result = r["results"][0]
                geocoded[project] = (
                    round(float(result["LATITUDE"]), 6),
                    round(float(result["LONGITUDE"]), 6)
                )
        except:
            pass
        time.sleep(0.05)

    for project, (lat, lon) in geocoded.items():
        mask = (df["project"] == project) & (df["latitude"].isna())
        df.loc[mask, "latitude"]  = lat
        df.loc[mask, "longitude"] = lon

    return df


@st.cache_data(ttl=86400)
def load_masterplan():
    fetched_at = datetime.now()
    dataset_id = "d_a8c3546b26712e35021f3a681d0353ae"
    poll_url   = f"https://api-open.data.gov.sg/v1/public/api/datasets/{dataset_id}/poll-download"
    for _ in range(15):
        r = requests.get(poll_url).json()
        if r.get("code") == 0:
            url = r.get("data", {}).get("url")
            if url:
                return requests.get(url).json(), fetched_at
        time.sleep(2)
    return None, fetched_at


@st.cache_data(ttl=86400)
def load_mrt_stations():
    """MRT/LRT stations from data.gov.sg (LTA station exits), deduped by name."""
    fetched_at = datetime.now()
    from config import AMENITY_COLORS
    dataset_id = "d_2c06c9fe8ae724b5d33efa1f203e2c38"
    poll_url   = f"https://api-open.data.gov.sg/v1/public/api/datasets/{dataset_id}/poll-download"
    for _ in range(10):
        r = requests.get(poll_url).json()
        if r.get("code") == 0:
            url = r.get("data", {}).get("url")
            if url:
                geojson  = requests.get(url).json()
                seen     = set()
                stations = []
                for f in geojson.get("features", []):
                    props = f.get("properties", {})
                    name  = props.get("NAME", "").strip()
                    if not name or name in seen:
                        continue
                    seen.add(name)
                    coords = f.get("geometry", {}).get("coordinates", [[]])
                    try:
                        flat  = coords[0]
                        lon_s = sum(c[0] for c in flat) / len(flat)
                        lat_s = sum(c[1] for c in flat) / len(flat)
                    except:
                        continue
                    clean = (name.upper()
                        .replace(" MRT STATION", "").replace(" LRT STATION", "")
                        .replace(" INTERCHANGE", "").replace(" STATION", "").strip())
                    rail_type  = props.get("RAIL_TYPE", "MRT")
                    color      = AMENITY_COLORS["lrt"] if "LRT" in rail_type.upper() else AMENITY_COLORS["mrt"]
                    stations.append({
                        "name":       clean,
                        "rail_type":  rail_type,
                        "line_label": rail_type,
                        "latitude":   lat_s,
                        "longitude":  lon_s,
                        "color":      color,
                    })
                return stations, fetched_at
        time.sleep(2)
    return [], fetched_at


@st.cache_data(ttl=86400)
def load_schools():
    """MOE school directory from data.gov.sg."""
    fetched_at = datetime.now()
    dataset_id = "d_688b934f82c1059ed0a6993d2a829089"
    poll_url   = f"https://api-open.data.gov.sg/v1/public/api/datasets/{dataset_id}/poll-download"
    for _ in range(10):
        r = requests.get(poll_url).json()
        if r.get("code") == 0:
            url = r.get("data", {}).get("url")
            if url:
                data    = requests.get(url).json()
                schools = []
                for row in data.get("value", data if isinstance(data, list) else []):
                    try:
                        schools.append({
                            "name":      row.get("school_name", ""),
                            "level":     row.get("mainlevel_code", "").upper().strip(),
                            "latitude":  float(row.get("latitude", 0)),
                            "longitude": float(row.get("longitude", 0)),
                        })
                    except:
                        pass
                return [s for s in schools if s["latitude"] != 0], fetched_at
        time.sleep(2)
    return [], fetched_at


def search_onemap_keyword(keyword, lat, lon, radius_m):
    """Keyword search on OneMap public API, filtered to radius. No auth required."""
    from utils import haversine
    results = []
    for page in range(1, 4):
        url = (
            f"https://www.onemap.gov.sg/api/common/elastic/search"
            f"?searchVal={keyword}&returnGeom=Y&getAddrDetails=Y&pageNum={page}"
        )
        try:
            r     = requests.get(url, timeout=10).json()
            items = r.get("results", [])
            if not items:
                break
            for item in items:
                try:
                    lat_i = float(item.get("LATITUDE", 0))
                    lon_i = float(item.get("LONGITUDE", 0))
                    if lat_i == 0 and lon_i == 0:
                        continue
                    dist = haversine(lat, lon, lat_i, lon_i)
                    if dist <= radius_m:
                        name = item.get("BUILDING", "").strip()
                        if not name or name == "NIL":
                            name = item.get("ADDRESS", "")
                        results.append({
                            "name":      name,
                            "latitude":  lat_i,
                            "longitude": lon_i,
                            "distance":  dist,
                        })
                except:
                    pass
        except:
            break
    seen, deduped = set(), []
    for r in results:
        if r["name"] not in seen:
            seen.add(r["name"])
            deduped.append(r)
    return deduped


def geocode_address(address):
    url = (
        f"https://www.onemap.gov.sg/api/common/elastic/search"
        f"?searchVal={address}&returnGeom=Y&getAddrDetails=Y&pageNum=1"
    )
    try:
        r = requests.get(url, timeout=10).json()
        if r.get("found", 0) > 0:
            result = r["results"][0]
            return float(result["LATITUDE"]), float(result["LONGITUDE"]), result.get("ADDRESS", address)
    except:
        pass
    return None, None, None
