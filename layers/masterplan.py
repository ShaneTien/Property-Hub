import pydeck as pdk
from utils import haversine
from config import LAND_USE_COLORS, DEFAULT_MP_COLOR


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
