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

TOOLTIP_MASTERPLAN = {
    "html": """
        <div style='font-size:12px;padding:8px;max-width:200px;line-height:1.8;font-family:sans-serif'>
        <b>{lu_desc}</b><br/>
        GPR: {gpr}
        </div>
    """,
    "style": {"backgroundColor": "white", "color": "black", "padding": "0"}
}

TOOLTIP_MIXED = {
    "html": """
        <div style='font-size:12px;padding:8px;max-width:260px;line-height:1.8;font-family:sans-serif'>
        <b>{project}{lu_desc}</b><br/>
        <span style='color:#666;font-size:11px'>{street}{gpr}</span>
        </div>
    """,
    "style": {"backgroundColor": "white", "color": "black", "padding": "0"}
}
