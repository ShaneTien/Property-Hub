import pydeck as pdk
from utils import make_circle


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
