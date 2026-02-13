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
