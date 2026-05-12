TOOLTIP_TRANSACTIONS = {
    "html": """
        <div style='font-size:12px;padding:8px;max-width:260px;line-height:1.8;font-family:sans-serif'>
        <b>{project}</b><br/>
        <span style='color:#666;font-size:11px'>{street} · D{district} · {market_segment}</span><br/>
        <b>S${psf} psf</b> &nbsp;|&nbsp; S${price_sgd}<br/>
        {area_sqft} sqft &nbsp;|&nbsp; Floor {floor_range}<br/>
        {tenure}<br/>
        <span style='color:#666;font-size:11px'>{property_type}</span>
        </div>
    """,
    "style": {"backgroundColor": "white", "color": "black", "padding": "0"}
}

TOOLTIP_GLS = {
    "html": """
        <div style='font-size:12px;padding:8px;max-width:260px;line-height:1.8;font-family:sans-serif'>
        <b>{location}</b><br/>
        <span style='color:#666;font-size:11px'>{devt_code}</span><br/>
        Tenure: {lease_yr} yrs &nbsp;|&nbsp; GPR: {gpr}<br/>
        Site area: {sa_sqm} sqm<br/>
        Units: {housing_un} &nbsp;|&nbsp; Bids: {no_of_bids}<br/>
        Awarded: {date_award}
        </div>
    """,
    "style": {"backgroundColor": "white", "color": "black", "padding": "0"}
}

TOOLTIP_MASTERPLAN = {
    "html": """
        <div style='font-size:12px;padding:8px;max-width:200px;line-height:1.8;font-family:sans-serif'>
        <b>{lu_desc}</b><br/>
        GPR: {gpr}
        </div>
    """,
    "style": {"backgroundColor": "white", "color": "black", "padding": "0"}
}

TOOLTIP_MRT = {
    "html": """
        <div style='font-size:12px;padding:8px;max-width:220px;line-height:1.8;font-family:sans-serif'>
        🚇 <b>{name}</b><br/>
        <span style='color:#666;font-size:11px'>{line_label} · {rail_type}</span>
        </div>
    """,
    "style": {"backgroundColor": "white", "color": "black", "padding": "0"}
}

TOOLTIP_AMENITY = {
    "html": """
        <div style='font-size:12px;padding:8px;max-width:200px;line-height:1.8;font-family:sans-serif'>
        <b>{name}</b><br/>
        <span style='color:#666;font-size:11px'>{theme}</span>
        </div>
    """,
    "style": {"backgroundColor": "white", "color": "black", "padding": "0"}
}

TOOLTIP_DEMOGRAPHICS = {
    "html": """
        <div style='font-size:12px;padding:8px;max-width:240px;line-height:1.8;font-family:sans-serif'>
        <b>{planning_area}</b><br/>
        Population: {total_pop}<br/>
        Density: {pop_density} /km²<br/>
        Young (0-24): {pct_young}<br/>
        Elderly (65+): {pct_elderly}<br/>
        HDB: {pct_hdb} &nbsp;|&nbsp; Private: {pct_private}
        </div>
    """,
    "style": {"backgroundColor": "white", "color": "black", "padding": "0"}
}
