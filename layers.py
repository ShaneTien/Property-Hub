import pydeck as pdk
from utils import psf_to_color, get_centroid, parse_date, make_circle, haversine
from config import LAND_USE_COLORS, DEFAULT_MP_COLOR


# ── TRANSACTION LAYER ────────────────────────────────────
def build_transaction_layer(filtered, tx_view):
    if len(filtered) == 0:
        return []

    if tx_view == "Heatmap":
        return [pdk.Layer(
            "HeatmapLayer",
            data=filtered[["latitude", "longitude", "psf"]],
            get_position=["longitude", "latitude"],
            get_weight="psf",
            radiusPixels=40,
            opacity=0.8,
        )]
    else:
        min_psf = filtered["psf"].min()
        max_psf = filtered["psf"].max()
        tx_map  = filtered.copy()
        tx_map["color"] = tx_map["psf"].apply(lambda x: psf_to_color(x, min_psf, max_psf))
        return [pdk.Layer(
            "ScatterplotLayer",
            data=tx_map,
            get_position=["longitude", "latitude"],
            get_fill_color="color",
            get_radius=50,
            pickable=True,
            opacity=0.8,
        )]


# ── GLS LAYER ────────────────────────────────────────────
def build_gls_layer(gls_geojson):
    if not gls_geojson:
        return []

    gls_polygons, gls_dots = [], []
    for f in gls_geojson.get("features", []):
        props  = f.get("properties", {})
        coords = f["geometry"]["coordinates"]
        lon_c, lat_c = get_centroid(coords)
        item = {
            "coordinates": coords,
            "location":    props.get("LOCATION", ""),
            "devt_code":   props.get("DEVT_CODE", ""),
            "lease_yr":    str(props.get("LEASE_YR", "")),
            "gpr":         str(props.get("GPR", "")),
            "housing_un":  str(props.get("HOUSING_UN", "")),
            "no_of_bids":  str(props.get("NO_OF_BIDS", "")),
            "date_award":  parse_date(props.get("DATE_AWARD")),
            "sa_sqm":      str(props.get("SA_SQM", "")),
        }
        gls_polygons.append(item)
        if lat_c and lon_c:
            gls_dots.append({**item, "latitude": lat_c, "longitude": lon_c})

    return [
        pdk.Layer(
            "PolygonLayer",
            data=gls_polygons,
            get_polygon="coordinates",
            get_fill_color=[255, 140, 0, 100],
            get_line_color=[255, 100, 0, 200],
            get_line_width=2,
            pickable=True,
            stroked=True,
            filled=True,
        ),
        pdk.Layer(
            "ScatterplotLayer",
            data=gls_dots,
            get_position=["longitude", "latitude"],
            get_fill_color=[255, 80, 0, 220],
            get_radius=40,
            pickable=True,
        ),
    ]


# ── MASTER PLAN LAYER ────────────────────────────────────
def build_masterplan_layer(mp_geojson, center_lat, center_lon, radius_m):
    if not mp_geojson:
        return []

    mp_data = []
    for f in mp_geojson.get("features", []):
        lu     = f.get("properties", {}).get("LU_DESC", "")
        gpr    = f.get("properties", {}).get("GPR", "")
        color  = LAND_USE_COLORS.get(lu.upper(), DEFAULT_MP_COLOR)
        coords = f["geometry"]["coordinates"]
        try:
            flat  = coords[0] if isinstance(coords[0][0], list) else coords
            c_lon = sum(c[0] for c in flat) / len(flat)
            c_lat = sum(c[1] for c in flat) / len(flat)
            if haversine(center_lat, center_lon, c_lat, c_lon) > radius_m * 2:
                continue
        except:
            continue
        mp_data.append({
            "coordinates": coords,
            "lu_desc":     lu,
            "gpr":         str(gpr),
            "color":       color,
        })

    return [pdk.Layer(
        "PolygonLayer",
        data=mp_data,
        get_polygon="coordinates",
        get_fill_color="color",
        get_line_color=[150, 150, 150, 80],
        get_line_width=1,
        pickable=True,
        stroked=True,
        filled=True,
    )]


# ── MRT LAYER ────────────────────────────────────────────
def build_mrt_layer(stations):
    if not stations:
        return []

    from config import MRT_LINE_COLORS, MRT_DEFAULT_COLOR
    import math

    OFFSET_M = 35  # metres between dots for interchange stations

    data = []
    for s in stations:
        lines     = s.get("lines", [])
        lat       = s.get("latitude")
        lon       = s.get("longitude")
        name      = s.get("name", "")
        rail_type = s.get("rail_type", "MRT")
        line_label = s.get("line_label", "")

        if not lines:
            # No line info — single grey dot
            data.append({
                "name":       name,
                "rail_type":  rail_type,
                "line_label": line_label,
                "line":       "",
                "latitude":   lat,
                "longitude":  lon,
                "color":      MRT_DEFAULT_COLOR,
            })
            continue

        n = len(lines)
        for i, line in enumerate(lines):
            color = MRT_LINE_COLORS.get(line, MRT_DEFAULT_COLOR)

            if n == 1:
                # Single line — no offset
                offset_lat = lat
                offset_lon = lon
            else:
                # Spread dots in a row horizontally
                # Centre offset so dots are symmetric around station point
                angle = math.pi / 2  # spread east-west
                step  = OFFSET_M / 111320
                offset = (i - (n - 1) / 2) * step
                offset_lat = lat
                offset_lon = lon + offset / math.cos(math.radians(lat))

            data.append({
                "name":       name,
                "rail_type":  rail_type,
                "line_label": line_label,
                "line":       line,
                "latitude":   offset_lat,
                "longitude":  offset_lon,
                "color":      color,
            })

    return [pdk.Layer(
        "ScatterplotLayer",
        data=data,
        get_position=["longitude", "latitude"],
        get_fill_color="color",
        get_radius=25,
        pickable=True,
        opacity=1.0,
    )]

# ── AMENITY LAYER ────────────────────────────────────────
def build_amenity_layer(amenity_data):
    if not amenity_data:
        return []
    data = [{
        "name":      a.get("name", ""),
        "theme":     a.get("theme", ""),
        "latitude":  a.get("latitude"),
        "longitude": a.get("longitude"),
        "color":     a.get("color", [180, 180, 180, 240]),
    } for a in amenity_data]
    return [pdk.Layer(
        "ScatterplotLayer",
        data=data,
        get_position=["longitude", "latitude"],
        get_fill_color="color",
        get_radius=35,
        pickable=True,
        opacity=0.9,
    )]


# ── RADIUS RING ──────────────────────────────────────────
def build_radius_ring(center_lat, center_lon, radius_m):
    ring_coords = make_circle(center_lat, center_lon, radius_m)
    return [
        pdk.Layer(
            "PolygonLayer",
            data=[{"coordinates": [ring_coords]}],
            get_polygon="coordinates",
            get_fill_color=[100, 150, 255, 30],
            get_line_color=[100, 150, 255, 200],
            get_line_width=3,
            stroked=True,
            filled=True,
        ),
        pdk.Layer(
            "ScatterplotLayer",
            data=[{"lat": center_lat, "lon": center_lon}],
            get_position=["lon", "lat"],
            get_fill_color=[50, 100, 255, 255],
            get_radius=30,
        ),
    ]


# ── TOOLTIPS ─────────────────────────────────────────────
TOOLTIP_TRANSACTIONS = {
    "html": """
        <div style='font-size:12px;padding:8px;max-width:260px;line-height:1.8;font-family:sans-serif'>
        <b>{project}</b><br/>
        <span style='color:#666;font-size:11px'>{street} · D{district} · {market_segment}</span><br/>
        <b>S${psf} psf</b> &nbsp;|&nbsp; S${price_sgd}<br/>
        {area_sqft} sqft &nbsp;|&nbsp; Floor {floor_range}<br/>
        {tenure}<br/>
        <span style='color:#666;font-size:11px'>{property_type}</span>
        </div>
    """,
    "style": {"backgroundColor": "white", "color": "black", "padding": "0"}
}

TOOLTIP_GLS = {
    "html": """
        <div style='font-size:12px;padding:8px;max-width:260px;line-height:1.8;font-family:sans-serif'>
        <b>{location}</b><br/>
        <span style='color:#666;font-size:11px'>{devt_code}</span><br/>
        Tenure: {lease_yr} yrs &nbsp;|&nbsp; GPR: {gpr}<br/>
        Site area: {sa_sqm} sqm<br/>
        Units: {housing_un} &nbsp;|&nbsp; Bids: {no_of_bids}<br/>
        Awarded: {date_award}
        </div>
    """,
    "style": {"backgroundColor": "white", "color": "black", "padding": "0"}
}

TOOLTIP_MASTERPLAN = {
    "html": """
        <div style='font-size:12px;padding:8px;max-width:200px;line-height:1.8;font-family:sans-serif'>
        <b>{lu_desc}</b><br/>
        GPR: {gpr}
        </div>
    """,
    "style": {"backgroundColor": "white", "color": "black", "padding": "0"}
}

TOOLTIP_MRT = {
    "html": """
        <div style='font-size:12px;padding:8px;max-width:220px;line-height:1.8;font-family:sans-serif'>
        🚇 <b>{name}</b><br/>
        <span style='color:#666;font-size:11px'>{line_label} · {rail_type}</span>
        </div>
    """,
    "style": {"backgroundColor": "white", "color": "black", "padding": "0"}
}

TOOLTIP_AMENITY = {
    "html": """
        <div style='font-size:12px;padding:8px;max-width:200px;line-height:1.8;font-family:sans-serif'>
        <b>{name}</b><br/>
        <span style='color:#666;font-size:11px'>{theme}</span>
        </div>
    """,
    "style": {"backgroundColor": "white", "color": "black", "padding": "0"}
}
