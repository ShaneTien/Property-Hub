import requests
import pandas as pd
import time
import os
import math
from pyproj import Transformer

TRANSFORMER = Transformer.from_crs("EPSG:3414", "EPSG:4326", always_xy=True)
ACCESS_KEY  = os.environ["URA_ACCESS_KEY"]
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "ura_transactions.csv")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}


def get_token():
    r = requests.get(
        "https://eservice.ura.gov.sg/uraDataService/insertNewToken/v1",
        headers={**HEADERS, "AccessKey": ACCESS_KEY}
    )
    return r.json()["Result"]


def get_batch(token, batch):
    url = f"https://eservice.ura.gov.sg/uraDataService/invokeUraDS/v1?service=PMI_Resi_Transaction&batch={batch}"
    r = requests.get(url, headers={**HEADERS, "AccessKey": ACCESS_KEY, "Token": token})
    return r.json().get("Result", [])


def geocode_onemap(project_name):
    try:
        url = (
            f"https://www.onemap.gov.sg/api/common/elastic/search"
            f"?searchVal={requests.utils.quote(project_name)}&returnGeom=Y&getAddrDetails=Y&pageNum=1"
        )
        r = requests.get(url, timeout=5).json()
        if r.get("found", 0) > 0:
            result = r["results"][0]
            return round(float(result["LATITUDE"]), 6), round(float(result["LONGITUDE"]), 6)
    except:
        pass
    return None, None


print("Getting URA token...")
token = get_token()
print(f"Token: {token[:10]}...")

rows = []
for batch in range(1, 5):
    print(f"Fetching batch {batch}/4...")
    data = get_batch(token, batch)
    for project in data:
        lat, lon = None, None
        try:
            x, y     = float(project.get("x")), float(project.get("y"))
            lon, lat = TRANSFORMER.transform(x, y)
            lat, lon = round(lat, 6), round(lon, 6)
        except:
            pass
        for t in project.get("transaction", []):
            price     = pd.to_numeric(t.get("price"), errors="coerce")
            area_sqm  = pd.to_numeric(t.get("area"),  errors="coerce")
            area_sqft = round(area_sqm * 10.7639, 0) if pd.notna(area_sqm) else None
            psf       = round(price / area_sqft, 0) if area_sqft and area_sqft > 0 else None
            rows.append({
                "project":        project.get("project"),
                "street":         project.get("street"),
                "market_segment": project.get("marketSegment"),
                "latitude":       lat,
                "longitude":      lon,
                "contract_date":  t.get("contractDate"),
                "area_sqm":       area_sqm,
                "area_sqft":      area_sqft,
                "price_sgd":      price,
                "psf":            psf,
                "property_type":  t.get("propertyType"),
                "tenure":         t.get("tenure"),
                "floor_range":    t.get("floorRange"),
                "type_of_sale":   t.get("typeOfSale"),
                "district":       t.get("district"),
            })
    print(f"  → {len(rows):,} rows so far")
    time.sleep(1)

df = pd.DataFrame(rows)

# Parse dates
df["month"] = df["contract_date"].str[:2]
df["year"]  = "20" + df["contract_date"].str[2:]
df["date"]  = pd.to_datetime(df["year"] + "-" + df["month"], format="%Y-%m", errors="coerce")

# Geocode missing projects
missing = df[df["latitude"].isna()]["project"].dropna().unique()
print(f"\nGeocoding {len(missing)} missing projects via OneMap...")
geocoded = {}
for i, project in enumerate(missing):
    lat, lon = geocode_onemap(project)
    if lat:
        geocoded[project] = (lat, lon)
    if i % 50 == 0:
        print(f"  {i}/{len(missing)}")
    time.sleep(0.05)

for project, (lat, lon) in geocoded.items():
    mask = (df["project"] == project) & (df["latitude"].isna())
    df.loc[mask, "latitude"]  = lat
    df.loc[mask, "longitude"] = lon

print(f"\nGeocoded {len(geocoded)}/{len(missing)} missing projects")

# Save
os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
df.to_csv(OUTPUT_PATH, index=False)
print(f"Saved {len(df):,} rows to {OUTPUT_PATH}")
