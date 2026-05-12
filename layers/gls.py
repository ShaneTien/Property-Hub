import pydeck as pdk
from utils import get_centroid, parse_date


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
