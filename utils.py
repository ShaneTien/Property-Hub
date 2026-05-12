import math


def haversine(lat1, lon1, lat2, lon2):
    """Straight-line distance in metres between two WGS84 coordinates."""
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def make_circle(lat, lon, radius_m, n=64):
    """Return a list of [lon, lat] pairs forming a circle polygon."""
    coords = []
    for i in range(n + 1):
        angle = 2 * math.pi * i / n
        dlat  = (radius_m / 111320) * math.cos(angle)
        dlon  = (radius_m / (111320 * math.cos(math.radians(lat)))) * math.sin(angle)
        coords.append([lon + dlon, lat + dlat])
    return coords


def psf_to_color(psf, min_psf, max_psf):
    """Map a PSF value to an RGBA colour from green (low) to red (high)."""
    ratio = min(max((psf - min_psf) / (max_psf - min_psf + 1), 0), 1)
    return [int(255 * ratio), int(255 * (1 - ratio)), 50, 180]


def parse_date(d):
    """Parse a YYYYMMDD integer or string to a readable date string."""
    if not d or str(d) == "0":
        return "N/A"
    try:
        from datetime import datetime
        return datetime.strptime(str(d), "%Y%m%d").strftime("%d %b %Y")
    except:
        return str(d)


def get_centroid(coordinates):
    """Return (lon, lat) centroid of a GeoJSON polygon coordinate array."""
    try:
        coords = coordinates[0]
        lons = [c[0] for c in coords]
        lats = [c[1] for c in coords]
        return sum(lons) / len(lons), sum(lats) / len(lats)
    except:
        return None, None


def bbox(lat, lon, radius_m):
    """Return (lat1, lon1, lat2, lon2) bounding box around a point."""
    dlat = radius_m / 111320
    dlon = radius_m / (111320 * math.cos(math.radians(lat)))
    return lat - dlat, lon - dlon, lat + dlat, lon + dlon
