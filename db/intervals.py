import sqlite3
import time
from pathlib import Path

import requests

MACROSTRAT_INTERVALS_URL = "https://macrostrat.org/api/v2/defs/intervals"
DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "intervals.sqlite"
CACHE_MAX_AGE_DAYS = 30


def init_db(db_path=None):
    db_path = db_path or DEFAULT_DB_PATH
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS intervals (
            int_id    INTEGER PRIMARY KEY,
            name      TEXT NOT NULL,
            abbrev    TEXT,
            t_age     REAL NOT NULL,
            b_age     REAL NOT NULL,
            int_type  TEXT NOT NULL,
            color     TEXT,
            timescale TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS _metadata (
            key   TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    conn.commit()
    return conn


def refresh_intervals(conn):
    resp = requests.get(MACROSTRAT_INTERVALS_URL, params={"all": "", "format": "json"}, timeout=30)
    resp.raise_for_status()
    data = resp.json().get("success", {}).get("data", [])
    if not data:
        return
    conn.execute("DELETE FROM intervals")
    for row in data:
        timescales = row.get("timescale") or ""
        if isinstance(timescales, list):
            timescales = ", ".join(timescales)
        conn.execute(
            "INSERT OR REPLACE INTO intervals (int_id, name, abbrev, t_age, b_age, int_type, color, timescale) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                row["int_id"],
                row["name"],
                row.get("abbrev", ""),
                row["t_age"],
                row["b_age"],
                row["int_type"],
                row.get("color", ""),
                timescales,
            ),
        )
    conn.execute(
        "INSERT OR REPLACE INTO _metadata (key, value) VALUES ('last_updated', ?)",
        (str(time.time()),),
    )
    conn.commit()


def get_intervals(conn, type_filter=None):
    if type_filter:
        if isinstance(type_filter, str):
            type_filter = [type_filter]
        placeholders = ", ".join("?" for _ in type_filter)
        rows = conn.execute(
            f"SELECT * FROM intervals WHERE int_type IN ({placeholders}) ORDER BY t_age",
            type_filter,
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM intervals ORDER BY t_age").fetchall()
    return [dict(r) for r in rows]


def ensure_cache_fresh(conn, max_age_days=CACHE_MAX_AGE_DAYS):
    row = conn.execute("SELECT value FROM _metadata WHERE key = 'last_updated'").fetchone()
    if row:
        last_updated = float(row["value"])
        age_days = (time.time() - last_updated) / 86400
        if age_days < max_age_days:
            count = conn.execute("SELECT COUNT(*) as c FROM intervals").fetchone()["c"]
            if count > 0:
                return
    refresh_intervals(conn)
