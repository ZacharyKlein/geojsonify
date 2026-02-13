import itertools

import requests

BASE_URL = "https://macrostrat.org/api/v2"


def fetch_map_at_point(lat, lng):
    """Fetch geologic map polygons at a single lat/lng point.

    Returns a list of GeoJSON feature dicts.
    """
    try:
        resp = requests.get(
            f"{BASE_URL}/geologic_units/map",
            params={"lat": lat, "lng": lng, "format": "geojson_bare"},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json().get("features", [])
    except (requests.RequestException, ValueError):
        return []


def _linspace(start, stop, n):
    if n <= 1:
        return [(start + stop) / 2]
    step = (stop - start) / (n - 1)
    return [start + i * step for i in range(n)]


def fetch_map_polygons(bbox, age_top=None, age_bottom=None, grid_n=5):
    """Fetch geologic map polygons across a bounding box by sampling a grid.

    Optionally filters by age range. Returns deduplicated GeoJSON feature dicts.
    """
    lats = _linspace(bbox["latmin"], bbox["latmax"], grid_n)
    lngs = _linspace(bbox["lngmin"], bbox["lngmax"], grid_n)

    seen_ids = set()
    features = []

    for lat, lng in itertools.product(lats, lngs):
        feats = fetch_map_at_point(lat, lng)
        for feat in feats:
            props = feat.get("properties", {})
            map_id = props.get("map_id")
            if not map_id or map_id in seen_ids:
                continue

            # Filter by age overlap if specified
            if age_top is not None or age_bottom is not None:
                poly_t = props.get("t_age")
                poly_b = props.get("b_age")
                if poly_t is not None and poly_b is not None:
                    if age_bottom is not None and poly_t >= age_bottom:
                        continue
                    if age_top is not None and poly_b <= age_top:
                        continue

            seen_ids.add(map_id)
            features.append(feat)

    return features


def fetch_units(bbox, interval_name=None, age_top=None, age_bottom=None):
    params = {
        "lngmin": bbox["lngmin"],
        "lngmax": bbox["lngmax"],
        "latmin": bbox["latmin"],
        "latmax": bbox["latmax"],
        "response": "long",
        "format": "json",
    }
    if interval_name:
        params["interval_name"] = interval_name
    if age_top is not None:
        params["age_top"] = age_top
    if age_bottom is not None:
        params["age_bottom"] = age_bottom

    resp = requests.get(f"{BASE_URL}/units", params=params, timeout=60)
    resp.raise_for_status()
    data = resp.json().get("success", {}).get("data", [])
    return data


def fetch_fossils(bbox, interval_name=None, age_top=None, age_bottom=None):
    params = {
        "lngmin": bbox["lngmin"],
        "lngmax": bbox["lngmax"],
        "latmin": bbox["latmin"],
        "latmax": bbox["latmax"],
        "format": "json",
    }
    if interval_name:
        params["interval_name"] = interval_name
    if age_top is not None:
        params["age_top"] = age_top
    if age_bottom is not None:
        params["age_bottom"] = age_bottom

    resp = requests.get(f"{BASE_URL}/fossils", params=params, timeout=60)
    resp.raise_for_status()
    data = resp.json().get("success", {}).get("data", [])
    return data
