import pydeck as pdk
from utils import psf_to_color


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
