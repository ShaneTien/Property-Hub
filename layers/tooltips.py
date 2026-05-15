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

TOOLTIP_MRT = {
    "html": """
        <div style='font-size:12px;padding:8px;max-width:220px;line-height:1.8;font-family:sans-serif'>
        <b>{name}</b><br/>
        <span style='color:#666;font-size:11px'>{line_label}</span>
        </div>
    """,
    "style": {"backgroundColor": "white", "color": "black", "padding": "0"}
}

TOOLTIP_AMENITY = {
    "html": """
        <div style='font-size:12px;padding:8px;max-width:220px;line-height:1.8;font-family:sans-serif'>
        <b>{name}</b><br/>
        <span style='color:#666;font-size:11px'>{category}{line_label}</span>
        </div>
    """,
    "style": {"backgroundColor": "white", "color": "black", "padding": "0"}
}

# Used when more than one layer type is active simultaneously
TOOLTIP_HEX = {
    "html": """
        <div style='font-size:12px;padding:8px;max-width:200px;line-height:1.8;font-family:sans-serif'>
        <b>Transactions: {elevationValue}</b>
        </div>
    """,
    "style": {"backgroundColor": "white", "color": "black", "padding": "0"}
}

# Used when multiple layer types are active simultaneously.
# Fields that are missing on a given layer type render as empty strings,
# so each layer naturally shows only its own relevant fields.
TOOLTIP_COMBINED = {
    "html": """
        <div style='font-size:12px;padding:8px;max-width:260px;line-height:1.6;font-family:sans-serif'>
        <b>{name}{project}{lu_desc}{elevationValue}</b>
        <span style='color:#666;font-size:11px;display:block'>{category}{line_label}{street}{gpr}</span>
        </div>
    """,
    "style": {"backgroundColor": "white", "color": "black", "padding": "0"}
}

TOOLTIP_MIXED = TOOLTIP_COMBINED
