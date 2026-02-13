import requests

BASE_URL = "https://macrostrat.org/api/v2"


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
