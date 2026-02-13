import requests

BASE_URL = "https://paleobiodb.org/data1.2"


def fetch_occurrences(bbox, taxa=None, interval=None, age_top=None, age_bottom=None):
    params = {
        "lngmin": bbox["lngmin"],
        "lngmax": bbox["lngmax"],
        "latmin": bbox["latmin"],
        "latmax": bbox["latmax"],
        "show": "coords,stratext,strat,geo,loc",
        "vocab": "pbdb",
        "limit": "all",
    }
    if taxa:
        if isinstance(taxa, list):
            taxa = ",".join(t.strip() for t in taxa if t.strip())
        if taxa:
            params["base_name"] = taxa
    if interval:
        params["interval"] = interval
    if age_top is not None:
        params["min_ma"] = age_top
    if age_bottom is not None:
        params["max_ma"] = age_bottom

    resp = requests.get(f"{BASE_URL}/occs/list.json", params=params, timeout=120)
    resp.raise_for_status()
    data = resp.json()
    records = data.get("records", [])
    return records
