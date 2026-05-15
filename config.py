# ── BASEMAP ──────────────────────────────────────────────
ONEMAP_BASEMAP = "https://www.onemap.gov.sg/maps/json/raster/mbstyle/Default.json"

# ── MASTER PLAN LAND USE COLOURS (official URA scheme) ───
LAND_USE_COLORS = {
    "RESIDENTIAL":                               [255, 218, 185, 180],
    "RESIDENTIAL WITH COMMERCIAL AT 1ST STOREY": [255, 200, 150, 180],
    "COMMERCIAL":                                [255, 0,   0,   180],
    "COMMERCIAL & RESIDENTIAL":                  [255, 160, 122, 180],
    "HOTEL":                                     [255, 105, 180, 180],
    "WHITE":                                     [255, 255, 255, 200],
    "BUSINESS 1":                                [153, 153, 255, 180],
    "BUSINESS 1 - WHITE":                        [180, 153, 255, 180],
    "BUSINESS 2":                                [102, 102, 204, 180],
    "BUSINESS 2 - WHITE":                        [130, 102, 204, 180],
    "BUSINESS PARK":                             [204, 153, 255, 180],
    "BUSINESS PARK - WHITE":                     [220, 180, 255, 180],
    "OPEN SPACE":                                [0,   180, 0,   180],
    "PARK":                                      [0,   153, 0,   180],
    "NATURE RESERVE":                            [0,   102, 0,   180],
    "BEACH AREA":                                [135, 206, 235, 180],
    "WATERBODY":                                 [0,   150, 255, 180],
    "TRANSPORT":                                 [200, 200, 200, 180],
    "ROAD":                                      [220, 220, 220, 180],
    "MASS RAPID TRANSIT":                        [160, 160, 160, 180],
    "CIVIC & COMMUNITY":                         [0,   220, 220, 180],
    "EDUCATIONAL INSTITUTION":                   [0,   191, 255, 180],
    "HEALTH & MEDICAL CARE":                     [255, 0,   128, 180],
    "PLACE OF WORSHIP":                          [210, 180, 140, 180],
    "COMMUNITY INSTITUTION":                     [100, 220, 220, 180],
    "UTILITY":                                   [255, 255, 0,   180],
    "SPECIAL USE":                               [200, 180, 160, 180],
    "RESERVE SITE":                              [211, 211, 211, 180],
    "CEMETERY":                                  [180, 180, 180, 180],
    "PORT / AIRPORT":                            [160, 160, 160, 180],
    "AGRICULTURE":                               [144, 238, 144, 180],
}
DEFAULT_MP_COLOR = [220, 220, 220, 120]

# ── AMENITY COLOURS ──────────────────────────────────────
AMENITY_COLORS = {
    "mrt":          [0,   102, 204, 240],
    "lrt":          [100, 160, 220, 240],
    "hospitals":    [220, 50,  50,  240],
    "malls":        [255, 100, 0,   240],
    "supermarkets": [255, 150, 0,   240],
    "schools":      [0,   153, 0,   240],
    "parks":        [0,   102, 0,   240],
    "cc":           [0,   180, 180, 240],
}

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
    {
        "layer":   "Master Plan 2025",
        "source":  "data.gov.sg — URA Master Plan 2025 Land Use",
        "url":     "https://data.gov.sg/datasets/d_a8c3546b26712e35021f3a681d0353ae/view",
        "api":     "https://api-open.data.gov.sg/v1/public/api/datasets/d_a8c3546b26712e35021f3a681d0353ae/poll-download",
        "updated": "Dec 2025",
        "dl_key":  "masterplan",
    },
]
