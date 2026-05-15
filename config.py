# ── BASEMAP ──────────────────────────────────────────────
ONEMAP_BASEMAP = "https://www.onemap.gov.sg/maps/json/raster/mbstyle/Default.json"

# ── DATA SOURCES SUMMARY ─────────────────────────────────
DATA_SOURCES = [
    {
        "layer":   "URA Transactions",
        "source":  "URA Data Service API",
        "url":     "https://www.ura.gov.sg/maps/api/",
        "api":     "https://eservice.ura.gov.sg/uraDataService/invokeUraDS/v1?service=PMI_Resi_Transaction&batch={1–4}",
        "updated": None,  # filled dynamically from CSV mtime
        "dl_key":  "ura_transactions",
    },
]
