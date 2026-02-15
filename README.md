# GeoJSONify Macro|Paleo

A Streamlit application for querying fossil occurrence data from [Macrostrat](https://macrostrat.org/) and [PaleobioDB](https://paleobiodb.org/) within a user-defined geographic region and stratigraphic range. Results are correlated by lithostratigraphic unit and exported as ArcGIS-compatible GeoJSON files organized by stage × unit.

## Features

- **Interactive map selection** — Draw a bounding box on a Leaflet map or enter coordinates manually to define your study area
- **Stratigraphic interval autocomplete** — Select upper/lower time bounds from 1,700+ cached ICS intervals (stages, epochs, periods, eras), with optional regional/biostratigraphic zones
- **Dual API queries** — Fetches geological units from Macrostrat and fossil occurrences from PaleobioDB in a single workflow
- **Occurrence–unit correlation** — Matches PBDB occurrences to Macrostrat lithostratigraphic units by temporal overlap and formation name
- **Stage × unit grouping** — Organizes results into bins by geologic stage and unit name
- **ArcGIS-compatible GeoJSON export** — Outputs one GeoJSON file per group with EPSG:4326 CRS, Point geometries, and flat (non-nested) properties
- **Bulk download** — Download all exported files as a single ZIP archive, or individually
- **Local interval cache** — Stratigraphic intervals are cached in SQLite and refreshed automatically every 30 days

## Requirements

- Python 3.10+
- System dependencies: none (pyogrio bundles its own GDAL)

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

```bash
streamlit run app.py
```

Then open http://localhost:8501 in your browser.

### Workflow

1. **Set region** — Draw a rectangle on the map or enter lat/lng bounds in the sidebar
2. **Set stratigraphic range** — Select upper (younger) and lower (older) interval bounds from the dropdown, or leave as "(none)" for no time filter
3. **Enter taxa** — Provide comma-separated taxon names (e.g., `Dinosauria, Mammalia`)
4. **Fetch Data** — Click to query both APIs; results appear as a summary table and color-coded map
5. **Export GeoJSON** — Click to write files to the `output/` directory and download as ZIP

### Example query

- **Region:** Western Interior US (lat 35–45, lng -112 to -100)
- **Stratigraphic range:** Campanian–Maastrichtian (Cretaceous)
- **Taxa:** `Dinosauria`

## Project structure

```
macrostrat-toolkit/
├── app.py                      # Streamlit UI entry point
├── api/
│   ├── macrostrat.py           # Macrostrat API client (units, fossils)
│   └── paleobiodb.py           # PaleobioDB API client (occurrences)
├── db/
│   └── intervals.py            # SQLite cache for stratigraphic intervals
├── processing/
│   ├── correlate.py            # Cross-correlate units with occurrences
│   └── geojson_export.py       # GeoJSON generation (EPSG:4326, ArcGIS compat)
├── requirements.txt
├── intervals.sqlite            # Auto-created local cache (gitignored)
└── output/                     # Generated GeoJSON files (gitignored)
```

## GeoJSON output format

Each exported file is a valid RFC 7946 GeoJSON FeatureCollection with:

- **CRS:** WGS 84 (EPSG:4326)
- **Geometry type:** Point
- **Properties per feature:** `occurrence_no`, `accepted_name`, `identified_name`, `early_interval`, `late_interval`, `max_ma`, `min_ma`, `formation`, `geological_group`, `environment`, `reference_no`, `collection_no`, `stage`, `unit_name`
- **Filename pattern:** `{stage}_{unit_name}.geojson`

Files can be opened directly in ArcGIS, QGIS, or any GeoJSON-compatible GIS software.

## Version history

### 0.1.0 (2026-02-13)

- Initial release
- Interactive Folium map with bounding box selection
- Macrostrat API client for geological units and fossils
- PaleobioDB API client for fossil occurrences with full result retrieval
- SQLite-backed stratigraphic interval cache (auto-refreshed every 30 days)
- Occurrence–unit correlation by temporal overlap and formation name matching
- Stage × unit grouping with summary table and color-coded preview map
- ArcGIS-compatible GeoJSON export (EPSG:4326, flat properties, Point geometries)
- Bulk ZIP download and individual file download links

## API references

- [Macrostrat API v2](https://macrostrat.org/api)
- [PaleobioDB API v1.2](https://paleobiodb.org/data1.2/)
