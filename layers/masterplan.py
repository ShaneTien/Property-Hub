import pydeck as pdk
from config import LAND_USE_COLORS, DEFAULT_MP_COLOR


def build_masterplan_layer(mp_geojson, opacity=0.6):
    if not mp_geojson:
        return []

    mp_data = []
    for f in mp_geojson.get("features", []):
        lu     = f.get("properties", {}).get("LU_DESC", "")
        gpr    = f.get("properties", {}).get("GPR", "")
        color  = LAND_USE_COLORS.get(lu.upper(), DEFAULT_MP_COLOR)
        coords = f["geometry"]["coordinates"]
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
        opacity=opacity,
        pickable=True,
        stroked=True,
        filled=True,
    )]
