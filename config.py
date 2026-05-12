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

# ── AMENITY GROUPS ───────────────────────────────────────
AMENITY_GROUPS = {
    "🚇 Transport (MRT/LRT)": {
        "color":  [0, 102, 204, 240],
        "source": "data.gov.sg (LTA)",
        "themes": []  # loaded separately from data.gov.sg
    },
    "🏥 Healthcare": {
        "color":  [204, 0, 0, 240],
        "source": "OneMap (MOH)",
        "themes": ["moh_hospitals", "vaccination_polyclinics", "registered_pharmacy", "blood_bank"]
    },
    "🏫 Schools & Education": {
        "color":  [0, 153, 0, 240],
        "source": "OneMap",
        "themes": ["cpe_pei_premises", "cetcentres"]
    },
    "🏛️ Community": {
        "color":  [204, 153, 0, 240],
        "source": "OneMap (PA, NLB)",
        "themes": ["libraries", "communityclubs", "ssot_hawkercentres", "eldercare", "sso"]
    },
    "🌳 Parks & Recreation": {
        "color":  [0, 180, 60, 240],
        "source": "OneMap (NParks)",
        "themes": ["nationalparks", "sportsg_sport_facilities", "nparks_parks"]
    },
    "🎭 Culture & Tourism": {
        "color":  [102, 0, 204, 240],
        "source": "OneMap (NHB, STB)",
        "themes": ["museum", "theatre", "historicsites", "monuments", "tourism"]
    },
    "🏨 Hotels": {
        "color":  [255, 140, 0, 240],
        "source": "OneMap (STB)",
        "themes": ["hotels"]
    },
    "🚒 Emergency Services": {
        "color":  [255, 50, 50, 240],
        "source": "OneMap (SCDF)",
        "themes": ["firestation", "aed_locations", "civildefencepublicshelters"]
    },
}

# ── DATA SOURCES SUMMARY ─────────────────────────────────
DATA_SOURCES = [
    {"Layer": "Transactions",   "Source": "URA Data Service",  "Updated": "Tue & Fri"},
    {"Layer": "GLS Sites",      "Source": "data.gov.sg (URA)", "Updated": "Dec 2025"},
    {"Layer": "Master Plan",    "Source": "data.gov.sg (URA)", "Updated": "Dec 2025"},
    {"Layer": "MRT Stations",   "Source": "data.gov.sg (LTA)", "Updated": "Ongoing"},
    {"Layer": "Amenities",      "Source": "OneMap Themes",     "Updated": "Various"},
]
