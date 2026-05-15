import pydeck as pdk
from utils import psf_to_color

# Green → yellow → red, matching the PSF low→high convention
_PSF_COLOR_RANGE = [
    [0,   200, 0,   200],
    [100, 220, 0,   200],
    [200, 220, 0,   200],
    [255, 180, 0,   200],
    [255, 100, 0,   200],
    [255, 0,   0,   200],
]


def build_transaction_layer(filtered, tx_view,
                             hex_radius=200, grid_size=500, extruded=False):
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
        return [pdk.Layer(
            "HexagonLayer",
            data=filtered[["latitude", "longitude", "psf"]].dropna(),
            get_position=["longitude", "latitude"],
            get_color_weight="psf",
            get_elevation_weight="psf",
            color_aggregation="MEAN",
            elevation_aggregation="SUM",
            radius=hex_radius,
            elevation_scale=1,
            extruded=extruded,
            pickable=True,
            auto_highlight=True,
            coverage=0.9,
            color_range=_PSF_COLOR_RANGE,
        )]

    if tx_view == "Grid":
        return [pdk.Layer(
            "GridLayer",
            data=filtered[["latitude", "longitude", "psf"]].dropna(),
            get_position=["longitude", "latitude"],
            get_color_weight="psf",
            get_elevation_weight="psf",
            color_aggregation="MEAN",
            elevation_aggregation="SUM",
            cell_size=grid_size,
            elevation_scale=1,
            extruded=extruded,
            pickable=True,
            auto_highlight=True,
            color_range=_PSF_COLOR_RANGE,
        )]

    # Points (default)
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
