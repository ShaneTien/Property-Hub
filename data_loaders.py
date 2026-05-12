import streamlit as st
import requests
import pandas as pd
import time
import math
from pyproj import Transformer

TRANSFORMER = Transformer.from_crs("EPSG:3414", "EPSG:4326", always_xy=True)


@st.cache_data(ttl=43200)
def load_transactions(access_key):
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
    return df


@st.cache_data(ttl=86400)
def load_gls():
    dataset_id = "d_0e2b42f98535686282031a42c9c7b05a"
    poll_url   = f"https://api-open.data.gov.sg/v1/public/api/datasets/{dataset_id}/poll-download"
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
    poll_url   = f"https://api-open.data.gov.sg/v1/public/api/datasets/{dataset_id}/poll-download"
    for _ in range(15):
        r = requests.get(poll_url).json()
        if r.get("code") == 0:
            url = r.get("data", {}).get("url")
            if url:
                return requests.get(url).json()
        time.sleep(2)
    return None


@st.cache_data(ttl=86400)
def load_mrt_stations():
    """Load MRT/LRT stations from URA Master Plan 2025, enriched with line codes."""
    from config import MRT_STATION_LINES, MRT_LINE_COLORS, MRT_DEFAULT_COLOR

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
                    geom   = f.get("geometry", {})
                    coords = geom.get("coordinates", [[]])
                    try:
                        flat  = coords[0]
                        lon_s = sum(c[0] for c in flat) / len(flat)
                        lat_s = sum(c[1] for c in flat) / len(flat)
                    except:
                        continue

                    # Look up line codes — try exact match then partial
                    name_upper = name.upper()
                    # Strip " MRT STATION" or " LRT STATION" suffix
                    clean = (name_upper
                        .replace(" MRT STATION", "")
                        .replace(" LRT STATION", "")
                        .replace(" INTERCHANGE", "")
                        .replace(" STATION", "")
                        .strip())
                    lines = MRT_STATION_LINES.get(clean, [])

                    # Derive colour from first line
                    color = MRT_LINE_COLORS.get(lines[0], MRT_DEFAULT_COLOR) if lines else MRT_DEFAULT_COLOR

                    # Build line label e.g. "EW/CC"
                    line_label = "/".join(lines) if lines else props.get("RAIL_TYPE", "MRT")

                    stations.append({
                        "name":       clean,
                        "rail_type":  props.get("RAIL_TYPE", "MRT"),
                        "lines":      lines,
                        "line_label": line_label,
                        "latitude":   lat_s,
                        "longitude":  lon_s,
                        "color":      color,
                    })
                return stations
        time.sleep(2)
    return []


@st.cache_data(ttl=82800)
def get_onemap_token(email, password):
    r = requests.post(
        "https://www.onemap.gov.sg/api/auth/post/getToken",
        json={"email": email, "password": password}
    )
    return r.json().get("access_token")


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


def load_amenities_onemap(token, themes, lat, lon, radius_m):
    from utils import bbox
    lat1, lon1, lat2, lon2 = bbox(lat, lon, radius_m)
    extents = f"{lat1},{lon1},{lat2},{lon2}"
    headers = {"Authorization": token}
    results = []
    for theme in themes:
        try:
            r = requests.get(
                "https://www.onemap.gov.sg/api/public/themesvc/retrieveTheme",
                params={"queryName": theme, "extents": extents},
                headers=headers,
                timeout=10
            ).json()
            for item in r.get("SrchResults", [])[1:]:
                try:
                    if item.get("Type") != "Point":
                        continue
                    latlng = item.get("LatLng", "")
                    lat_i  = float(latlng.split(",")[0])
                    lon_i  = float(latlng.split(",")[1])
                    results.append({
                        "name":      item.get("NAME", ""),
                        "theme":     theme,
                        "latitude":  lat_i,
                        "longitude": lon_i,
                    })
                except:
                    pass
        except:
            pass
    return results
    
@st.cache_data(ttl=86400)
def load_onemap_themes(token):
    """Fetch all available OneMap themes grouped by category."""
    headers = {"Authorization": token}
    try:
        r = requests.get(
            "https://www.onemap.gov.sg/api/public/themesvc/getAllThemesInfo",
            params={"moreInfo": "Y"},
            headers=headers,
            timeout=10
        ).json()
        themes = r.get("Theme_Names", [])
        grouped = {}
        for t in themes:
            cat = t.get("CATEGORY") or "Other"
            if cat not in grouped:
                grouped[cat] = []
            grouped[cat].append({
                "name":      t.get("THEMENAME", ""),
                "queryName": t.get("QUERYNAME", ""),
            })
        return grouped
    except:
        return {}

def search_onemap_keyword(keyword, lat, lon, radius_m):
    """Search OneMap for a keyword and return nearby results."""
    from utils import haversine
    results = []
    # Try multiple pages
    for page in range(1, 4):
        url = (
            f"https://www.onemap.gov.sg/api/common/elastic/search"
            f"?searchVal={keyword}&returnGeom=Y&getAddrDetails=Y&pageNum={page}"
        )
        try:
            r = requests.get(url, timeout=10).json()
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
                            "theme":     keyword,
                            "latitude":  lat_i,
                            "longitude": lon_i,
                            "distance":  dist,
                        })
                except:
                    pass
        except:
            break
    # Deduplicate by name
    seen = set()
    deduped = []
    for r in results:
        if r["name"] not in seen:
            seen.add(r["name"])
            deduped.append(r)
    return deduped


@st.cache_data(ttl=86400)
def load_schools():
    """Load MOE schools from data.gov.sg."""
    dataset_id = "d_688b934f82c1059ed0a6993d2a829089"
    poll_url   = f"https://api-open.data.gov.sg/v1/public/api/datasets/{dataset_id}/poll-download"
    for _ in range(10):
        r = requests.get(poll_url).json()
        if r.get("code") == 0:
            url = r.get("data", {}).get("url")
            if url:
                data = requests.get(url).json()
                schools = []
                for row in data.get("value", data if isinstance(data, list) else []):
                    try:
                        schools.append({
                            "name":      row.get("school_name", ""),
                            "theme":     row.get("mainlevel_code", ""),
                            "latitude":  float(row.get("latitude", 0)),
                            "longitude": float(row.get("longitude", 0)),
                        })
                    except:
                        pass
                return [s for s in schools if s["latitude"] != 0]
        time.sleep(2)
    return []

@st.cache_data(ttl=86400)
def load_planning_area_boundaries():
    """MP2019 planning area polygons with names."""
    dataset_id = "d_bf4d24df9129d5a8ff8cf82e20959ee0"
    poll_url   = f"https://api-open.data.gov.sg/v1/public/api/datasets/{dataset_id}/poll-download"
    for _ in range(10):
        r = requests.get(poll_url).json()
        if r.get("code") == 0:
            url = r.get("data", {}).get("url")
            if url:
                return requests.get(url).json()
        time.sleep(2)
    return None


@st.cache_data(ttl=86400)
def load_demographics():
    """
    Loads Census 2020 population by age and dwelling type,
    returns a dict keyed by planning area name.
    """
    results = {}

    # Age data
    age_url = "https://data.gov.sg/api/action/datastore_search?resource_id=d_d95ae740c0f8961a0b10435836660ce0&limit=10000"
    try:
        age_data = requests.get(age_url, timeout=15).json().get("result", {}).get("records", [])
        for row in age_data:
            pa = row.get("PA", "").upper().strip()
            if not pa or pa == "TOTAL":
                continue
            if pa not in results:
                results[pa] = {"total_pop": 0, "young": 0, "elderly": 0, "dwelling": {}}
            age_grp = row.get("AG", "")
            pop = int(row.get("Pop", 0) or 0)
            results[pa]["total_pop"] += pop
            if age_grp in ["0_to_4", "5_to_9", "10_to_14", "15_to_19", "20_to_24"]:
                results[pa]["young"] += pop
            if age_grp in ["65_to_69", "70_to_74", "75_to_79", "80_to_84", "85_and_over"]:
                results[pa]["elderly"] += pop
    except:
        pass

    # Dwelling data
    dwell_url = "https://data.gov.sg/api/action/datastore_search?resource_id=d_7f243956483d5901f237e6f87b096636&limit=10000"
    try:
        dwell_data = requests.get(dwell_url, timeout=15).json().get("result", {}).get("records", [])
        for row in dwell_data:
            pa = row.get("PA", "").upper().strip()
            if not pa or pa == "TOTAL":
                continue
            if pa not in results:
                results[pa] = {"total_pop": 0, "young": 0, "elderly": 0, "dwelling": {}}
            dwell_type = row.get("DT", "")
            pop = int(row.get("Pop", 0) or 0)
            results[pa]["dwelling"][dwell_type] = results[pa]["dwelling"].get(dwell_type, 0) + pop
    except:
        pass

    return results

def build_planning_area_data(boundaries_geojson, demographics):
    """Merge planning area boundaries with demographic stats."""
    if not boundaries_geojson:
        return []

    planning_areas = []
    for f in boundaries_geojson.get("features", []):
        props = f.get("properties", {})
        pa_name = props.get("PLN_AREA_N", props.get("PLANAREA", "")).upper().strip()
        coords  = f["geometry"]["coordinates"]
        demo    = demographics.get(pa_name, {})

        total   = demo.get("total_pop", 0)
        young   = demo.get("young", 0)
        elderly = demo.get("elderly", 0)
        dwell   = demo.get("dwelling", {})

        hdb_keys     = [k for k in dwell if "HDB" in k.upper() or "PUBLIC" in k.upper()]
        private_keys = [k for k in dwell if "PRIVATE" in k.upper() or "CONDOMINIUM" in k.upper() or "LANDED" in k.upper()]
        hdb_pop      = sum(dwell[k] for k in hdb_keys)
        private_pop  = sum(dwell[k] for k in private_keys)
        dwell_total  = sum(dwell.values()) or 1

        # Estimate area in km² from polygon (rough)
        try:
            flat  = coords[0] if isinstance(coords[0][0], list) else coords
            lons  = [c[0] for c in flat]
            lats  = [c[1] for c in flat]
            width = (max(lons) - min(lons)) * 111 * abs(math.cos(math.radians(sum(lats)/len(lats))))
            height= (max(lats) - min(lats)) * 111
            area_km2 = width * height * 0.7  # rough polygon fill factor
        except:
            area_km2 = 1

        planning_areas.append({
            "coordinates":  coords,
            "planning_area": pa_name,
            "total_pop":    total,
            "pct_young":    (young / total * 100) if total else 0,
            "pct_elderly":  (elderly / total * 100) if total else 0,
            "pct_hdb":      (hdb_pop / dwell_total * 100),
            "pct_private":  (private_pop / dwell_total * 100),
            "pop_density":  (total / area_km2) if area_km2 else 0,
        })

    return planning_areas
