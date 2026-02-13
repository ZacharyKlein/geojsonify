import re
from pathlib import Path

import geopandas as gpd
from shapely.geometry import Point, box, shape
from shapely.validation import make_valid


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


def _base_filename(stage, unit_name):
    return f"{_sanitize_filename(stage)}_{_sanitize_filename(unit_name)}"


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
    filename = f"{_base_filename(stage, unit_name)}_points.geojson"
    out_path = output_dir / filename
    gdf.to_file(str(out_path), driver="GeoJSON")
    return out_path


def export_polygon_geojson(polygon_features, stage, unit_name, bbox, output_dir="output"):
    """Export polygon features for a stage×unit group, clipped to the bounding box.

    polygon_features: list of GeoJSON feature dicts from the Macrostrat map API.
    bbox: dict with latmin, latmax, lngmin, lngmax.
    Returns the output Path, or None if no valid polygons.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    clip_box = box(bbox["lngmin"], bbox["latmin"], bbox["lngmax"], bbox["latmax"])

    rows = []
    for feat in polygon_features:
        try:
            geom = shape(feat["geometry"])
            if not geom.is_valid:
                geom = make_valid(geom)
        except Exception:
            continue

        try:
            clipped = geom.intersection(clip_box)
        except Exception:
            continue
        if clipped.is_empty:
            continue

        props = {}
        for key in ("map_id", "name", "strat_name", "lith", "descrip",
                     "t_age", "b_age", "best_int_name", "color"):
            val = feat.get("properties", {}).get(key)
            if isinstance(val, (list, dict)):
                val = str(val)
            props[key] = val
        props["stage"] = stage
        props["unit_name"] = unit_name
        rows.append({"geometry": clipped, **props})

    if not rows:
        return None

    gdf = gpd.GeoDataFrame(rows, crs="EPSG:4326")
    filename = f"{_base_filename(stage, unit_name)}_polygons.geojson"
    out_path = output_dir / filename
    gdf.to_file(str(out_path), driver="GeoJSON")
    return out_path
