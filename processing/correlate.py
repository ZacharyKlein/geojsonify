from collections import defaultdict


def assign_stage(occurrence):
    early = occurrence.get("early_interval", "") or ""
    late = occurrence.get("late_interval", "") or ""
    if not early:
        return "Unknown"
    if not late or late == early:
        return early
    return f"{early}\u2013{late}"


def assign_unit(occurrence, macrostrat_units):
    occ_fm = (occurrence.get("formation") or "").strip().lower()
    occ_max = occurrence.get("max_ma")
    occ_min = occurrence.get("min_ma")

    best_match = None
    best_score = -1

    for unit in macrostrat_units:
        score = 0

        # Temporal overlap check
        u_top = unit.get("t_age")
        u_bot = unit.get("b_age")
        if occ_max is not None and occ_min is not None and u_top is not None and u_bot is not None:
            overlap_top = max(occ_min, u_top)
            overlap_bot = min(occ_max, u_bot)
            if overlap_top >= overlap_bot:
                continue
            score += 1
        else:
            continue

        # Formation name match
        unit_fm = (unit.get("Fm") or unit.get("strat_name_long") or "").strip().lower()
        if occ_fm and unit_fm and occ_fm in unit_fm:
            score += 10

        if score > best_score:
            best_score = score
            best_match = unit

    if best_match is None:
        return None
    return best_match.get("strat_name_long") or best_match.get("unit_name") or str(best_match.get("unit_id", ""))


def build_stage_unit_groups(occurrences, macrostrat_units):
    groups = defaultdict(list)
    for occ in occurrences:
        stage = assign_stage(occ)
        unit_name = assign_unit(occ, macrostrat_units) or "Unassigned"
        groups[(stage, unit_name)].append(occ)
    return dict(groups)


def fetch_polygons_for_groups(groups, progress_callback=None):
    """Fetch map polygons by querying at unique occurrence locations per group.

    For each group, samples up to ~20 unique occurrence locations and queries the
    Macrostrat map API to find the polygons that underlie those occurrences.

    Returns a dict mapping (stage, unit_name) -> list of GeoJSON feature dicts,
    deduplicated by map_id within each group.
    """
    from api.macrostrat import fetch_map_at_point

    matched = defaultdict(list)
    group_items = list(groups.items())
    total = len(group_items)

    for idx, ((stage, unit_name), occs) in enumerate(group_items):
        if unit_name == "Unassigned":
            if progress_callback:
                progress_callback((idx + 1) / total)
            continue

        # Collect unique lat/lng pairs, sample up to 5
        seen_coords = set()
        sample_points = []
        for occ in occs:
            lat, lng = occ.get("lat"), occ.get("lng")
            if lat is None or lng is None:
                continue
            lat, lng = float(lat), float(lng)
            key = (round(lat, 2), round(lng, 2))
            if key not in seen_coords:
                seen_coords.add(key)
                sample_points.append((lat, lng))
            if len(sample_points) >= 5:
                break

        seen_ids = set()
        for lat, lng in sample_points:
            feats = fetch_map_at_point(lat, lng)
            for feat in feats:
                map_id = feat.get("properties", {}).get("map_id")
                if map_id and map_id not in seen_ids:
                    seen_ids.add(map_id)
                    matched[(stage, unit_name)].append(feat)

        if progress_callback:
            progress_callback((idx + 1) / total)

    return dict(matched)
