import pydeck as pdk
from utils import psf_to_color

# Green → yellow → red, low→high PSF (RGB, not RGBA)
_PSF_COLOR_RANGE = [
    [0,   200, 0  ],
    [100, 220, 0  ],
    [200, 220, 0  ],
    [255, 180, 0  ],
    [255, 100, 0  ],
    [255, 0,   0  ],
]


def build_transaction_layer(filtered, tx_view,
                             hex_radius=500, grid_size=1000, extruded=False):
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
        data = filtered[["latitude", "longitude", "psf"]].dropna().to_dict("records")
        return [pdk.Layer(
            "HexagonLayer",
            data=data,
            get_position=["longitude", "latitude"],
            get_color_weight="psf",
            get_elevation_weight="psf",
            color_aggregation="MEAN",
            elevation_aggregation="SUM",
            radius=hex_radius,
            elevation_scale=4,
            extruded=extruded,
            pickable=True,
            coverage=0.85,
            color_range=_PSF_COLOR_RANGE,
            opacity=0.8,
        )]

    if tx_view == "Grid":
        data = filtered[["latitude", "longitude", "psf"]].dropna().to_dict("records")
        return [pdk.Layer(
            "GridLayer",
            data=data,
            get_position=["longitude", "latitude"],
            get_color_weight="psf",
            get_elevation_weight="psf",
            color_aggregation="MEAN",
            elevation_aggregation="SUM",
            cell_size=grid_size,
            elevation_scale=4,
            extruded=extruded,
            pickable=True,
            color_range=_PSF_COLOR_RANGE,
            opacity=0.8,
        )]

    # Points — radius in metres, clamped to pixel bounds so they scale on zoom
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
