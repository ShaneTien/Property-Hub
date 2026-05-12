@st.cache_data(ttl=86400)
def load_gls_sites():
    dataset_id = "d_0e2b42f98535686282031a42c9c7b05a"
    
    # For GeoJSON, skip initiate-download and go straight to poll-download
    poll_url = f"https://api-open.data.gov.sg/v1/public/api/datasets/{dataset_id}/poll-download"
    
    for attempt in range(10):
        r = requests.get(poll_url)
        data = r.json()
        if data.get("code") == 0:
            download_url = data.get("data", {}).get("url")
            if download_url:
                geojson = requests.get(download_url).json()
                return geojson
        import time; time.sleep(2)
    
    raise Exception("Could not download GLS data after retries")
