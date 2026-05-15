import pydeck as pdk
from utils import psf_to_color


def build_transaction_layer(filtered, tx_view,
                             hex_radius=200, grid_size=400,
                             extruded=False, max_elevation=500):
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

    if tx_view == "Hexagon":
        data = filtered[["latitude", "longitude"]].dropna().to_dict("records")
        return [pdk.Layer(
            "HexagonLayer",
            data=data,
            get_position=["longitude", "latitude"],
            radius=hex_radius,
            elevation_range=[0, max_elevation],
            extruded=extruded,
            pickable=True,
            auto_highlight=True,
            coverage=1,
            opacity=0.8,
        )]

    if tx_view == "Grid":
        data = filtered[["latitude", "longitude"]].dropna().to_dict("records")
        return [pdk.Layer(
            "GridLayer",
            data=data,
            get_position=["longitude", "latitude"],
            cell_size=grid_size,
            elevation_range=[0, max_elevation],
            extruded=extruded,
            pickable=True,
            auto_highlight=True,
            opacity=0.8,
        )]

    # Points
    min_psf = filtered["psf"].min()
    max_psf = filtered["psf"].max()
    tx_map  = filtered.copy()
    tx_map["color"] = tx_map["psf"].apply(lambda x: psf_to_color(x, min_psf, max_psf))
    return [pdk.Layer(
        "ScatterplotLayer",
        data=tx_map,
        get_position=["longitude", "latitude"],
        get_fill_color="color",
        get_radius=60,
        radius_min_pixels=2,
        radius_max_pixels=12,
        pickable=True,
        opacity=0.8,
    )]
