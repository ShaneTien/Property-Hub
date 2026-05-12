import pydeck as pdk


def _density_color(value, min_val, max_val):
    if max_val == min_val:
        return [200, 200, 200, 160]
    ratio = min(max((value - min_val) / (max_val - min_val), 0), 1)
    r = int(255 * ratio)
    b = int(255 * (1 - ratio))
    return [r, 50, b, 160]


def build_demographics_layer(planning_areas, metric):
    """
    planning_areas: list of dicts with keys:
        coordinates, planning_area, total_pop, pct_young, pct_elderly,
        pct_hdb, pct_private, pop_density
    metric: "density" | "age" | "dwelling"
    """
    if not planning_areas:
        return []

    values = []
    for pa in planning_areas:
        if metric == "density":
            values.append(pa.get("pop_density", 0))
        elif metric == "age":
            values.append(pa.get("pct_elderly", 0))
        elif metric == "dwelling":
            values.append(pa.get("pct_private", 0))

    min_val = min(values) if values else 0
    max_val = max(values) if values else 1

    data = []
    for pa, val in zip(planning_areas, values):
        data.append({
            "coordinates":   pa["coordinates"],
            "planning_area": pa.get("planning_area", ""),
            "total_pop":     f"{pa.get('total_pop', 0):,}",
            "pct_young":     f"{pa.get('pct_young', 0):.1f}%",
            "pct_elderly":   f"{pa.get('pct_elderly', 0):.1f}%",
            "pct_hdb":       f"{pa.get('pct_hdb', 0):.1f}%",
            "pct_private":   f"{pa.get('pct_private', 0):.1f}%",
            "pop_density":   f"{pa.get('pop_density', 0):,.0f}",
            "color":         _density_color(val, min_val, max_val),
        })

    return [pdk.Layer(
        "PolygonLayer",
        data=data,
        get_polygon="coordinates",
        get_fill_color="color",
        get_line_color=[100, 100, 100, 100],
        get_line_width=1,
        pickable=True,
        stroked=True,
        filled=True,
    )]
