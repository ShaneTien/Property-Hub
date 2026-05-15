import pydeck as pdk


def build_mrt_layer(stations):
    if not stations:
        return []
    return [pdk.Layer(
        "ScatterplotLayer",
        data=stations,
        get_position=["longitude", "latitude"],
        get_fill_color="color",
        get_radius=28,
        pickable=True,
        opacity=1.0,
    )]
