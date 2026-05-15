import pydeck as pdk


def build_amenity_layer(amenity_data):
    if not amenity_data:
        return []
    data = [{
        "name":      a.get("name", ""),
        "category":  a.get("category", ""),
        "line_label": a.get("line_label", ""),
        "latitude":  a.get("latitude"),
        "longitude": a.get("longitude"),
        "color":     a.get("color", [180, 180, 180, 240]),
    } for a in amenity_data]
    return [pdk.Layer(
        "ScatterplotLayer",
        data=data,
        get_position=["longitude", "latitude"],
        get_fill_color="color",
        get_radius=35,
        pickable=True,
        opacity=0.9,
    )]
