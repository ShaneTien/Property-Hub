import requests
import json
import gzip
import os
import time

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "masterplan.geojson.gz")

print("Fetching Master Plan 2025 from data.gov.sg...")
dataset_id = "d_a8c3546b26712e35021f3a681d0353ae"
poll_url   = f"https://api-open.data.gov.sg/v1/public/api/datasets/{dataset_id}/poll-download"

for attempt in range(15):
    r = requests.get(poll_url).json()
    if r.get("code") == 0:
        url = r.get("data", {}).get("url")
        if url:
            print(f"Downloading GeoJSON...")
            geojson = requests.get(url).json()
            os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
            with gzip.open(OUTPUT_PATH, "wt", encoding="utf-8") as f:
                json.dump(geojson, f)
            size_mb = os.path.getsize(OUTPUT_PATH) / 1_048_576
            print(f"Saved {len(geojson.get('features', [])):,} features -> {OUTPUT_PATH} ({size_mb:.1f} MB compressed)")
            break
    print(f"Waiting for download URL (attempt {attempt + 1}/15)...")
    time.sleep(2)
else:
    print("ERROR: Could not obtain download URL after 15 attempts.")
    raise SystemExit(1)
