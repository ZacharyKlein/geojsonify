import re
from pathlib import Path

import geopandas as gpd
from shapely.geometry import Point

PROPERTIES = [
    "occurrence_no",
    "accepted_name",
    "identified_name",
    "early_interval",
    "late_interval",
    "max_ma",
    "min_ma",
    "formation",
    "geological_group",
    "environment",
    "reference_no",
    "collection_no",
]


def _sanitize_filename(name):
    name = re.sub(r'[<>:"/\\|?*]', "_", name)
    name = re.sub(r"\s+", "_", name)
    name = re.sub(r"_+", "_", name)
    return name.strip("_")[:200]


def export_geojson(occurrences, stage, unit_name, output_dir="output"):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    for occ in occurrences:
        lng = occ.get("lng")
        lat = occ.get("lat")
        if lng is None or lat is None:
            continue
        props = {}
        for key in PROPERTIES:
            val = occ.get(key)
            if isinstance(val, (list, dict)):
                val = str(val)
            props[key] = val
        props["stage"] = stage
        props["unit_name"] = unit_name
        rows.append({"geometry": Point(float(lng), float(lat)), **props})

    if not rows:
        return None

    gdf = gpd.GeoDataFrame(rows, crs="EPSG:4326")
    filename = f"{_sanitize_filename(stage)}_{_sanitize_filename(unit_name)}.geojson"
    out_path = output_dir / filename
    gdf.to_file(str(out_path), driver="GeoJSON")
    return out_path
