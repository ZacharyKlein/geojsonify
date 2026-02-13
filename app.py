import io
import json
import zipfile
from pathlib import Path

import folium
import streamlit as st
from folium.plugins import Draw
from streamlit_folium import st_folium

from api.macrostrat import fetch_units
from api.paleobiodb import fetch_occurrences
from db.intervals import ensure_cache_fresh, get_intervals, init_db
from processing.correlate import build_stage_unit_groups
from processing.geojson_export import export_geojson

st.set_page_config(page_title="Macrostrat Toolkit", layout="wide")
st.title("Macrostrat Toolkit")
st.caption("Query Macrostrat & PaleobioDB, export ArcGIS-compatible GeoJSON by stage × unit")

# ── Interval cache ──────────────────────────────────────────────────────────
conn = init_db()
ensure_cache_fresh(conn)

ICS_TYPES = ["age", "epoch", "period", "era", "eon"]
TYPE_PRIORITY = {t: i for i, t in enumerate(ICS_TYPES)}


@st.cache_data
def load_intervals(include_regional):
    type_filter = None if include_regional else ICS_TYPES
    intervals = get_intervals(init_db(), type_filter=type_filter)
    intervals.sort(key=lambda x: (TYPE_PRIORITY.get(x["int_type"], 99), x["t_age"]))
    return intervals


# ── Sidebar ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Region")

    col1, col2 = st.columns(2)
    lat_min = col1.number_input("Lat min", value=35.0, min_value=-90.0, max_value=90.0, step=0.5)
    lat_max = col2.number_input("Lat max", value=45.0, min_value=-90.0, max_value=90.0, step=0.5)
    col3, col4 = st.columns(2)
    lng_min = col3.number_input("Lng min", value=-112.0, min_value=-180.0, max_value=180.0, step=0.5)
    lng_max = col4.number_input("Lng max", value=-100.0, min_value=-180.0, max_value=180.0, step=0.5)

    # Folium map with draw control
    center_lat = (lat_min + lat_max) / 2
    center_lng = (lng_min + lng_max) / 2
    m = folium.Map(location=[center_lat, center_lng], zoom_start=5)
    folium.Rectangle(
        bounds=[[lat_min, lng_min], [lat_max, lng_max]],
        color="blue",
        fill=True,
        fill_opacity=0.1,
    ).add_to(m)
    Draw(
        draw_options={
            "polyline": False,
            "polygon": False,
            "circle": False,
            "marker": False,
            "circlemarker": False,
            "rectangle": True,
        },
        edit_options={"edit": False},
    ).add_to(m)
    map_data = st_folium(m, height=300, width=None, key="bbox_map")

    # Update bbox from drawn rectangle
    if map_data and map_data.get("last_active_drawing"):
        coords = map_data["last_active_drawing"]["geometry"]["coordinates"][0]
        lngs = [c[0] for c in coords]
        lats = [c[1] for c in coords]
        drawn_lng_min, drawn_lng_max = min(lngs), max(lngs)
        drawn_lat_min, drawn_lat_max = min(lats), max(lats)
        if (drawn_lat_min != lat_min or drawn_lat_max != lat_max
                or drawn_lng_min != lng_min or drawn_lng_max != lng_max):
            st.session_state["lat_min"] = drawn_lat_min
            st.session_state["lat_max"] = drawn_lat_max
            st.session_state["lng_min"] = drawn_lng_min
            st.session_state["lng_max"] = drawn_lng_max

    st.divider()
    st.header("Stratigraphic Range")

    include_regional = st.checkbox("Include regional/biostratigraphic zones", value=False)
    intervals = load_intervals(include_regional)
    interval_options = ["(none)"] + [
        f"{iv['name']} ({iv['t_age']}–{iv['b_age']} Ma)" for iv in intervals
    ]

    upper_idx = st.selectbox("Upper bound (younger)", options=range(len(interval_options)),
                             format_func=lambda i: interval_options[i], index=0, key="upper_bound")
    lower_idx = st.selectbox("Lower bound (older)", options=range(len(interval_options)),
                             format_func=lambda i: interval_options[i], index=0, key="lower_bound")

    age_top = None
    age_bottom = None
    selected_interval_name = None
    if upper_idx > 0:
        age_top = intervals[upper_idx - 1]["t_age"]
    if lower_idx > 0:
        age_bottom = intervals[lower_idx - 1]["b_age"]
    if upper_idx > 0 and lower_idx > 0 and upper_idx == lower_idx:
        selected_interval_name = intervals[upper_idx - 1]["name"]

    st.divider()
    st.header("Taxa")
    taxa_input = st.text_area("Comma-separated taxa", value="Dinosauria", height=80)

    st.divider()
    fetch_btn = st.button("Fetch Data", type="primary", width="stretch")

# ── Main area ───────────────────────────────────────────────────────────────
bbox = {"latmin": lat_min, "latmax": lat_max, "lngmin": lng_min, "lngmax": lng_max}

if fetch_btn:
    taxa_list = [t.strip() for t in taxa_input.split(",") if t.strip()] if taxa_input else []

    with st.spinner("Fetching Macrostrat units..."):
        units = fetch_units(bbox, interval_name=selected_interval_name,
                            age_top=age_top, age_bottom=age_bottom)
    st.info(f"Macrostrat: {len(units)} units returned")

    with st.spinner("Fetching PBDB occurrences..."):
        occurrences = fetch_occurrences(bbox, taxa=taxa_list,
                                        age_top=age_top, age_bottom=age_bottom)
    st.info(f"PaleobioDB: {len(occurrences)} occurrences returned")

    if not occurrences:
        st.warning("No occurrences found. Try adjusting your search parameters.")
        st.stop()

    with st.spinner("Correlating data..."):
        groups = build_stage_unit_groups(occurrences, units)

    st.session_state["groups"] = groups
    st.session_state["occurrences"] = occurrences

    # Summary table
    st.subheader("Stage × Unit Groups")
    summary_rows = []
    for (stage, unit_name), occs in sorted(groups.items()):
        summary_rows.append({"Stage": stage, "Unit": unit_name, "Occurrences": len(occs)})
    st.dataframe(summary_rows, width="stretch")

    # Preview map
    st.subheader("Occurrence Map")
    preview_map = folium.Map(location=[center_lat, center_lng], zoom_start=5)
    folium.Rectangle(
        bounds=[[lat_min, lng_min], [lat_max, lng_max]],
        color="blue",
        fill=False,
    ).add_to(preview_map)

    # Color by stage
    stage_colors = {}
    palette = [
        "#e6194b", "#3cb44b", "#ffe119", "#4363d8", "#f58231",
        "#911eb4", "#42d4f4", "#f032e6", "#bfef45", "#fabed4",
        "#469990", "#dcbeff", "#9A6324", "#800000", "#aaffc3",
    ]
    color_idx = 0
    for (stage, _), occs in groups.items():
        if stage not in stage_colors:
            stage_colors[stage] = palette[color_idx % len(palette)]
            color_idx += 1
        color = stage_colors[stage]
        for occ in occs:
            lng = occ.get("lng")
            lat = occ.get("lat")
            if lng is None or lat is None:
                continue
            folium.CircleMarker(
                location=[lat, lng],
                radius=4,
                color=color,
                fill=True,
                fill_opacity=0.7,
                popup=f"{occ.get('accepted_name', '?')}<br>{stage}",
            ).add_to(preview_map)

    st_folium(preview_map, height=500, width=None, key="preview_map")

# ── Export ──────────────────────────────────────────────────────────────────
if "groups" in st.session_state and st.session_state["groups"]:
    st.divider()
    if st.button("Export GeoJSON", type="secondary", width="stretch"):
        output_dir = Path("output")
        exported_files = []
        groups = st.session_state["groups"]

        progress = st.progress(0)
        total = len(groups)
        for i, ((stage, unit_name), occs) in enumerate(sorted(groups.items())):
            path = export_geojson(occs, stage, unit_name, output_dir=output_dir)
            if path:
                exported_files.append(path)
            progress.progress((i + 1) / total)

        st.success(f"Exported {len(exported_files)} GeoJSON files to `output/`")

        # Zip download
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for fp in exported_files:
                zf.write(fp, fp.name)
        zip_buffer.seek(0)
        st.download_button(
            label="Download all as ZIP",
            data=zip_buffer,
            file_name="macrostrat_geojson.zip",
            mime="application/zip",
        )

        # Individual file links
        st.subheader("Exported Files")
        for fp in exported_files:
            with open(fp, "r") as f:
                st.download_button(
                    label=fp.name,
                    data=f.read(),
                    file_name=fp.name,
                    mime="application/geo+json",
                    key=f"dl_{fp.name}",
                )

# ── GeoJSON Preview ───────────────────────────────────────────────────────
output_dir = Path("output")
geojson_files = sorted(output_dir.glob("*.geojson")) if output_dir.exists() else []

if geojson_files:
    st.divider()
    st.subheader("Preview GeoJSON")

    selected_file = st.selectbox(
        "Select a GeoJSON file",
        options=geojson_files,
        format_func=lambda p: p.name,
        key="geojson_preview_select",
    )

    if st.button("Preview", type="secondary", key="preview_geojson_btn"):
        st.session_state["preview_file"] = str(selected_file)

    if "preview_file" in st.session_state:
        preview_path = Path(st.session_state["preview_file"])
        if preview_path.exists():
            with open(preview_path, "r") as f:
                geojson_data = json.load(f)

            # Compute map center from features
            lats, lngs = [], []
            for feat in geojson_data.get("features", []):
                coords = feat.get("geometry", {}).get("coordinates")
                if coords and len(coords) >= 2:
                    lngs.append(coords[0])
                    lats.append(coords[1])

            if lats and lngs:
                map_center = [sum(lats) / len(lats), sum(lngs) / len(lngs)]
            else:
                map_center = [center_lat, center_lng]

            preview = folium.Map(location=map_center, zoom_start=6)
            folium.GeoJson(
                geojson_data,
                name=preview_path.name,
                popup=folium.GeoJsonPopup(
                    fields=["accepted_name", "stage", "unit_name"],
                    aliases=["Name", "Stage", "Unit"],
                ),
                marker=folium.CircleMarker(
                    radius=5,
                    fill=True,
                    fill_opacity=0.7,
                    color="#e6194b",
                ),
            ).add_to(preview)

            st.caption(f"Previewing: **{preview_path.name}** ({len(geojson_data.get('features', []))} features)")
            st_folium(preview, height=500, width=None, key="geojson_preview_map")
