import pydeck as pdk
import math
from config import MRT_LINE_COLORS, MRT_DEFAULT_COLOR


def build_mrt_layer(stations):
    if not stations:
        return []

    OFFSET_M = 35

    data = []
    for s in stations:
        lines      = s.get("lines", [])
        lat        = s.get("latitude")
        lon        = s.get("longitude")
        name       = s.get("name", "")
        rail_type  = s.get("rail_type", "MRT")
        line_label = s.get("line_label", "")

        if not lines:
            data.append({
                "name": name, "rail_type": rail_type,
                "line_label": line_label, "line": "",
                "latitude": lat, "longitude": lon,
                "color": MRT_DEFAULT_COLOR,
            })
            continue

        n = len(lines)
        for i, line in enumerate(lines):
            color = MRT_LINE_COLORS.get(line, MRT_DEFAULT_COLOR)
            if n == 1:
                offset_lat, offset_lon = lat, lon
            else:
                step       = OFFSET_M / 111320
                offset     = (i - (n - 1) / 2) * step
                offset_lat = lat
                offset_lon = lon + offset / math.cos(math.radians(lat))
            data.append({
                "name": name, "rail_type": rail_type,
                "line_label": line_label, "line": line,
                "latitude": offset_lat, "longitude": offset_lon,
                "color": color,
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
