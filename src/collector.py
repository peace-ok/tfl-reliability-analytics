"""
TfL Line Status Collector
Polls the TfL Unified API for line status across all major modes and stores
timestamped observations in SQLite. Logs every run so collection gaps can be
identified and flagged during analysis.

Usage:
    python src/collector.py --once          # single run
    python src/collector.py                 # continuous, every POLL_MINUTES
"""

import argparse
import json
import logging
import os
import sqlite3
import time
from datetime import datetime, timezone

import requests

from severity_map import classify_severity

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
MODES = "tube,overground,elizabeth-line,dlr,tram"
API_URL = f"https://api.tfl.gov.uk/Line/Mode/{MODES}/Status"
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "tfl_status.db")
POLL_MINUTES = 10
APP_KEY = os.environ.get("TFL_APP_KEY")  # optional, raises rate limits

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("collector")


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
SCHEMA = """
CREATE TABLE IF NOT EXISTS line_status_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    observed_at_utc TEXT NOT NULL,           -- ISO 8601, UTC
    line_id TEXT NOT NULL,
    line_name TEXT NOT NULL,
    mode TEXT NOT NULL,
    severity_level INTEGER NOT NULL,          -- TfL statusSeverity code
    severity_description TEXT,
    is_disrupted INTEGER NOT NULL,            -- 1/0 from explicit mapping
    is_excluded INTEGER NOT NULL,             -- 1 if code excluded from analysis
    is_planned INTEGER NOT NULL,              -- 1 if planned works (best effort)
    reason TEXT                               -- raw disruption reason text
);

CREATE TABLE IF NOT EXISTS collection_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_at_utc TEXT NOT NULL,
    success INTEGER NOT NULL,
    lines_recorded INTEGER,
    error TEXT
);

CREATE INDEX IF NOT EXISTS idx_line_date
    ON line_status_history (line_name, observed_at_utc);
"""


def get_db() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)
    return conn


# ---------------------------------------------------------------------------
# Collection
# ---------------------------------------------------------------------------
def is_planned_disruption(status: dict) -> bool:
    """Best-effort identification of planned engineering works.

    TfL marks planned closures in the disruption category and typically in the
    reason text. This heuristic is deliberately conservative and documented in
    docs/severity_mapping.md; misclassification risk is discussed there.
    """
    disruption = status.get("disruption") or {}
    category = (disruption.get("category") or "").lower()
    reason = (status.get("reason") or "").lower()
    planned_markers = ("plannedwork", "planned work", "planned closure",
                      "engineering work", "planned engineering")
    return category == "plannedwork" or any(m in reason for m in planned_markers)


def collect_once(conn: sqlite3.Connection) -> None:
    run_at = datetime.now(timezone.utc).isoformat()
    params = {"app_key": APP_KEY} if APP_KEY else {}
    try:
        resp = requests.get(API_URL, params=params, timeout=30)
        resp.raise_for_status()
        lines = resp.json()
    except Exception as exc:  # noqa: BLE001 - we log and record all failures
        log.error("Collection failed: %s", exc)
        conn.execute(
            "INSERT INTO collection_log (run_at_utc, success, lines_recorded, error) "
            "VALUES (?, 0, 0, ?)",
            (run_at, str(exc)),
        )
        conn.commit()
        return

    rows = 0
    for line in lines:
        for status in line.get("lineStatuses", []):
            severity = status.get("statusSeverity")
            desc = status.get("statusSeverityDescription")
            disrupted, excluded = classify_severity(severity)
            conn.execute(
                "INSERT INTO line_status_history "
                "(observed_at_utc, line_id, line_name, mode, severity_level, "
                " severity_description, is_disrupted, is_excluded, is_planned, reason) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    run_at,
                    line.get("id"),
                    line.get("name"),
                    line.get("modeName"),
                    severity,
                    desc,
                    int(disrupted),
                    int(excluded),
                    int(is_planned_disruption(status)),
                    status.get("reason"),
                ),
            )
            rows += 1

    conn.execute(
        "INSERT INTO collection_log (run_at_utc, success, lines_recorded, error) "
        "VALUES (?, 1, ?, NULL)",
        (run_at, rows),
    )
    conn.commit()
    log.info("Recorded %d line statuses", rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="run a single collection")
    args = parser.parse_args()

    conn = get_db()
    if args.once:
        collect_once(conn)
        return
    log.info("Starting continuous collection every %d minutes", POLL_MINUTES)
    while True:
        collect_once(conn)
        time.sleep(POLL_MINUTES * 60)


if __name__ == "__main__":
    main()
