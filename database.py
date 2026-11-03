"""Safe SQLite persistence for current weather, anonymous vision events and alerts.

Existing sensor_readings rows are intentionally untouched by schema initialization.
"""
from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

PROJECT_DIR = Path(__file__).resolve().parent
if os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
    _DEFAULT_DB = Path("/tmp/campus.db")
else:
    _DEFAULT_DB = PROJECT_DIR / "database" / "campus.db"
DATABASE_PATH = Path(os.environ.get("RCERT_DATABASE_PATH", _DEFAULT_DB))


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    global DATABASE_PATH
    try:
        DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        DATABASE_PATH = Path("/tmp/campus.db")
        DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH, timeout=15)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 15000")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def initialize_database() -> None:
    """Create only new tables/indexes; never drop or rewrite legacy records."""
    with connect() as db:
        db.execute("PRAGMA journal_mode = WAL")
        db.executescript("""
            CREATE TABLE IF NOT EXISTS weather_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kind TEXT NOT NULL CHECK(kind IN ('weather', 'air_quality')),
                payload_json TEXT NOT NULL,
                fetched_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_weather_kind_fetched
                ON weather_snapshots(kind, fetched_at DESC);

            CREATE TABLE IF NOT EXISTS iot_readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                temperature REAL,
                humidity REAL,
                electricity REAL,
                water REAL,
                occupancy REAL,
                source TEXT NOT NULL DEFAULT 'ESP32_IoT',
                classification TEXT NOT NULL DEFAULT 'actual_iot'
                    CHECK(classification = 'actual_iot')
            );
            CREATE INDEX IF NOT EXISTS idx_iot_time ON iot_readings(timestamp DESC);

            CREATE TABLE IF NOT EXISTS vision_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT NOT NULL UNIQUE,
                camera_id TEXT NOT NULL,
                zone_id TEXT,
                session_id TEXT NOT NULL,
                track_id TEXT NOT NULL,
                event_type TEXT NOT NULL CHECK(event_type IN ('entry', 'exit')),
                direction TEXT NOT NULL CHECK(direction IN ('entry', 'exit')),
                occurred_at TEXT NOT NULL,
                ingested_at TEXT NOT NULL,
                classification TEXT NOT NULL DEFAULT 'actual_camera'
                    CHECK(classification = 'actual_camera')
            );
            CREATE INDEX IF NOT EXISTS idx_vision_time ON vision_events(occurred_at DESC);
            CREATE INDEX IF NOT EXISTS idx_vision_camera_time ON vision_events(camera_id, occurred_at DESC);
            CREATE INDEX IF NOT EXISTS idx_vision_zone_time ON vision_events(zone_id, occurred_at DESC);

            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                severity TEXT NOT NULL CHECK(severity IN ('info', 'warning', 'critical')),
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                source TEXT NOT NULL,
                support_json TEXT NOT NULL DEFAULT '{}',
                dedupe_key TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                acknowledged_at TEXT,
                resolved_at TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_alert_status_time
                ON alerts(resolved_at, acknowledged_at, created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_alert_category_time
                ON alerts(category, created_at DESC);

            CREATE TABLE IF NOT EXISTS camera_config (
                camera_id TEXT PRIMARY KEY,
                zone_id TEXT,
                line_json TEXT NOT NULL,
                entry_direction TEXT NOT NULL,
                confidence REAL NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_camera_config_updated ON camera_config(updated_at DESC);

            CREATE TABLE IF NOT EXISTS cameras (
                camera_id TEXT PRIMARY KEY,
                display_name TEXT NOT NULL,
                zone_id TEXT,
                status TEXT NOT NULL CHECK(status IN ('disconnected', 'connecting', 'connected', 'stopped', 'error')),
                session_id TEXT,
                last_error TEXT,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_cameras_status ON cameras(status, updated_at DESC);

            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value_json TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
        """)
        # Deduplicate legacy active alerts: keep only the latest per category, title, and active state
        db.execute("""
            DELETE FROM alerts
            WHERE resolved_at IS NULL AND id NOT IN (
                SELECT MAX(id) FROM alerts WHERE resolved_at IS NULL GROUP BY category, title
            )
        """)


def save_weather_snapshot(kind: str, payload: dict[str, Any], fetched_at: str) -> None:
    if kind not in {"weather", "air_quality"}:
        raise ValueError("unsupported weather snapshot kind")
    with connect() as db:
        db.execute(
            "INSERT INTO weather_snapshots(kind, payload_json, fetched_at) VALUES (?, ?, ?)",
            (kind, json.dumps(payload, separators=(",", ":"), allow_nan=False), fetched_at),
        )


def latest_weather_snapshot(kind: str) -> dict[str, Any] | None:
    with connect() as db:
        row = db.execute(
            "SELECT payload_json, fetched_at FROM weather_snapshots WHERE kind = ? ORDER BY id DESC LIMIT 1",
            (kind,),
        ).fetchone()
    if not row:
        return None
    try:
        payload = json.loads(row["payload_json"])
    except (TypeError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    return {"payload": payload, "fetched_at": row["fetched_at"]}


def list_weather_snapshots(kind: str = "weather", limit: int = 50) -> list[dict[str, Any]]:
    limit = max(1, min(int(limit), 200))
    with connect() as db:
        rows = db.execute(
            "SELECT id, payload_json, fetched_at FROM weather_snapshots WHERE kind = ? ORDER BY id DESC LIMIT ?",
            (kind, limit),
        ).fetchall()
    results = []
    for row in rows:
        try:
            payload = json.loads(row["payload_json"])
            results.append({"id": row["id"], "payload": payload, "fetched_at": row["fetched_at"]})
        except (TypeError, json.JSONDecodeError):
            continue
    return results


DEFAULT_SETTINGS = {
    "temperature_unit": "celsius",
    "wind_unit": "kmh",
    "refresh_interval_sec": 300,
    "theme": "dark",
    "presentation_mode": False,
    "render_quality": "high",
}


def get_setting(key: str, default: Any = None) -> Any:
    with connect() as db:
        row = db.execute("SELECT value_json FROM app_settings WHERE key = ?", (key,)).fetchone()
    if not row:
        return DEFAULT_SETTINGS.get(key, default)
    try:
        return json.loads(row["value_json"])
    except (TypeError, json.JSONDecodeError):
        return DEFAULT_SETTINGS.get(key, default)


def set_setting(key: str, value: Any, now: str | None = None) -> None:
    now = now or utc_now()
    val_json = json.dumps(value, separators=(",", ":"), allow_nan=False)
    with connect() as db:
        db.execute(
            "INSERT INTO app_settings(key, value_json, updated_at) VALUES(?, ?, ?) ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json, updated_at=excluded.updated_at",
            (key, val_json, now),
        )


def get_all_settings() -> dict[str, Any]:
    settings = dict(DEFAULT_SETTINGS)
    with connect() as db:
        rows = db.execute("SELECT key, value_json FROM app_settings").fetchall()
    for row in rows:
        try:
            settings[row["key"]] = json.loads(row["value_json"])
        except (TypeError, json.JSONDecodeError):
            pass
    return settings


def upsert_alert(*, category: str, severity: str, title: str, message: str, source: str,
                 support: dict[str, Any], dedupe_key: str, now: str | None = None) -> int:
    now = now or utc_now()
    with connect() as db:
        row = db.execute(
            "SELECT id FROM alerts WHERE (dedupe_key = ? OR (category = ? AND title = ?)) AND resolved_at IS NULL ORDER BY id DESC LIMIT 1",
            (dedupe_key, category, title),
        ).fetchone()
        if row:
            db.execute(
                "UPDATE alerts SET severity=?, title=?, message=?, source=?, support_json=?, dedupe_key=?, updated_at=? WHERE id=?",
                (severity, title, message, source, json.dumps(support, separators=(",", ":"), allow_nan=False), dedupe_key, now, row["id"]),
            )
            return int(row["id"])
        cursor = db.execute(
            "INSERT INTO alerts(category,severity,title,message,source,support_json,dedupe_key,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)",
            (category, severity, title, message, source, json.dumps(support, separators=(",", ":"), allow_nan=False), dedupe_key, now, now),
        )
        return int(cursor.lastrowid)


def list_alerts(*, category: str | None = None, severity: str | None = None,
                state: str | None = None, query: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
    clauses: list[str] = []
    params: list[Any] = []
    if category:
        clauses.append("category = ?")
        params.append(category)
    if severity:
        clauses.append("severity = ?")
        params.append(severity)
    if state == "unread":
        clauses.append("acknowledged_at IS NULL AND resolved_at IS NULL")
    elif state == "active":
        clauses.append("resolved_at IS NULL")
    elif state == "resolved":
        clauses.append("resolved_at IS NOT NULL")
    elif state == "acknowledged":
        clauses.append("acknowledged_at IS NOT NULL AND resolved_at IS NULL")
    if query:
        clauses.append("(title LIKE ? OR message LIKE ? OR source LIKE ?)")
        needle = f"%{query[:120]}%"
        params.extend((needle, needle, needle))
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    limit = max(1, min(int(limit), 200))
    with connect() as db:
        rows = db.execute(
            f"SELECT * FROM alerts{where} ORDER BY created_at DESC, id DESC LIMIT ?",
            (*params, limit),
        ).fetchall()
    result: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        try:
            item["support"] = json.loads(item.pop("support_json"))
        except (TypeError, json.JSONDecodeError):
            item["support"] = {}
        result.append(item)
    return result


def change_alert_state(alert_id: int, action: str, now: str | None = None) -> dict[str, Any] | None:
    if action not in {"acknowledge", "resolve"}:
        raise ValueError("unsupported alert action")
    now = now or utc_now()
    column = "acknowledged_at" if action == "acknowledge" else "resolved_at"
    with connect() as db:
        row = db.execute("SELECT id FROM alerts WHERE id = ?", (alert_id,)).fetchone()
        if not row:
            return None
        if action == "resolve":
            db.execute(
                "UPDATE alerts SET acknowledged_at=COALESCE(acknowledged_at, ?), resolved_at=COALESCE(resolved_at, ?), updated_at=? WHERE id=?",
                (now, now, now, alert_id),
            )
        else:
            db.execute(
                f"UPDATE alerts SET {column}=COALESCE({column}, ?), updated_at=? WHERE id=?",
                (now, now, alert_id),
            )
        row = db.execute("SELECT * FROM alerts WHERE id = ?", (alert_id,)).fetchone()
    item = dict(row)
    try:
        item["support"] = json.loads(item.pop("support_json"))
    except (TypeError, json.JSONDecodeError):
        item["support"] = {}
    return item


def insert_vision_event(event: dict[str, Any]) -> dict[str, Any]:
    with connect() as db:
        duplicate = db.execute(
            """SELECT event_id,camera_id,zone_id,session_id,track_id,event_type,direction,occurred_at,ingested_at,classification
               FROM vision_events WHERE camera_id=? AND session_id=? AND track_id=? AND direction=?
               AND ABS(julianday(occurred_at)-julianday(?)) <= (3.0/86400.0)
               ORDER BY id DESC LIMIT 1""",
            (event["camera_id"], event["session_id"], event["track_id"], event["direction"], event["occurred_at"]),
        ).fetchone()
        if duplicate:
            return {**dict(duplicate), "duplicate": True}
        cursor = db.execute(
            "INSERT INTO vision_events(event_id,camera_id,zone_id,session_id,track_id,event_type,direction,occurred_at,ingested_at,classification) VALUES(?,?,?,?,?,?,?,?,?,'actual_camera')",
            (event["event_id"], event["camera_id"], event.get("zone_id"), event["session_id"], event["track_id"], event["event_type"], event["direction"], event["occurred_at"], event.get("ingested_at") or utc_now()),
        )
        row_id = cursor.lastrowid
        if row_id is None:
            raise RuntimeError("SQLite did not return the inserted event id")
    return {**event, "id": int(row_id), "duplicate": False, "classification": "actual_camera"}


def list_vision_events(*, camera_id: str | None = None, zone_id: str | None = None,
                       since: str | None = None, until: str | None = None, limit: int = 200) -> list[dict[str, Any]]:
    clauses = ["classification='actual_camera'"]
    params: list[Any] = []
    for field, value in (("camera_id", camera_id), ("zone_id", zone_id)):
        if value:
            clauses.append(f"{field} = ?")
            params.append(value)
    if since:
        clauses.append("occurred_at >= ?")
        params.append(since)
    if until:
        clauses.append("occurred_at <= ?")
        params.append(until)
    limit = max(1, min(int(limit), 1000))
    with connect() as db:
        rows = db.execute(
            f"SELECT event_id,camera_id,zone_id,session_id,track_id,event_type,direction,occurred_at,ingested_at,classification FROM vision_events WHERE {' AND '.join(clauses)} ORDER BY occurred_at DESC,id DESC LIMIT ?",
            (*params, limit),
        ).fetchall()
    return [dict(row) for row in rows]


def summarize_vision_events(*, since: str | None = None, until: str | None = None) -> dict[str, Any]:
    clauses = ["classification='actual_camera'"]
    params: list[Any] = []
    if since:
        clauses.append("occurred_at >= ?")
        params.append(since)
    if until:
        clauses.append("occurred_at <= ?")
        params.append(until)
    where = " WHERE " + " AND ".join(clauses)
    with connect() as db:
        totals = db.execute(
            f"SELECT COUNT(*) AS total, SUM(event_type='entry') AS entries, SUM(event_type='exit') AS exits, COUNT(DISTINCT camera_id) AS cameras FROM vision_events{where}",
            params,
        ).fetchone()
        by_camera = db.execute(
            f"SELECT camera_id,SUM(event_type='entry') AS entries,SUM(event_type='exit') AS exits,COUNT(*) AS events FROM vision_events{where} GROUP BY camera_id ORDER BY events DESC",
            params,
        ).fetchall()
    entries = int(totals["entries"] or 0)
    exits = int(totals["exits"] or 0)
    return {
        "classification": "actual_camera",
        "source": "validated anonymous camera events",
        "total_events": int(totals["total"] or 0),
        "entries": entries,
        "exits": exits,
        "net_flow": entries - exits,
        "camera_count": int(totals["cameras"] or 0),
        "by_camera": [dict(row) for row in by_camera],
    }


def upsert_camera(*, camera_id: str, display_name: str, zone_id: str | None, status: str,
                  session_id: str | None = None, last_error: str | None = None,
                  now: str | None = None) -> dict[str, Any]:
    if status not in {"disconnected", "connecting", "connected", "stopped", "error"}:
        raise ValueError("invalid camera state")
    now = now or utc_now()
    with connect() as db:
        db.execute(
            "INSERT INTO cameras(camera_id,display_name,zone_id,status,session_id,last_error,updated_at) VALUES(?,?,?,?,?,?,?) ON CONFLICT(camera_id) DO UPDATE SET display_name=excluded.display_name,zone_id=excluded.zone_id,status=excluded.status,session_id=excluded.session_id,last_error=excluded.last_error,updated_at=excluded.updated_at",
            (camera_id, display_name, zone_id, status, session_id, last_error, now),
        )
        row = db.execute("SELECT * FROM cameras WHERE camera_id=?", (camera_id,)).fetchone()
    return dict(row)


def list_cameras() -> list[dict[str, Any]]:
    with connect() as db:
        rows = db.execute("SELECT * FROM cameras ORDER BY display_name,camera_id").fetchall()
    return [dict(row) for row in rows]


def save_camera_config(*, camera_id: str, zone_id: str | None, line: dict[str, Any],
                       entry_direction: str, confidence: float, now: str | None = None) -> dict[str, Any]:
    now = now or utc_now()
    line_json = json.dumps(line, separators=(",", ":"), allow_nan=False)
    with connect() as db:
        db.execute(
            "INSERT INTO camera_config(camera_id,zone_id,line_json,entry_direction,confidence,updated_at) VALUES(?,?,?,?,?,?) ON CONFLICT(camera_id) DO UPDATE SET zone_id=excluded.zone_id,line_json=excluded.line_json,entry_direction=excluded.entry_direction,confidence=excluded.confidence,updated_at=excluded.updated_at",
            (camera_id, zone_id, line_json, entry_direction, confidence, now),
        )
        row = db.execute("SELECT * FROM camera_config WHERE camera_id=?", (camera_id,)).fetchone()
    item = dict(row)
    item["line"] = json.loads(item.pop("line_json"))
    return item


def get_camera_config(camera_id: str) -> dict[str, Any] | None:
    with connect() as db:
        row = db.execute("SELECT * FROM camera_config WHERE camera_id=?", (camera_id,)).fetchone()
    if not row:
        return None
    item = dict(row)
    item["line"] = json.loads(item.pop("line_json"))
    return item


def database_health() -> bool:
    with connect() as db:
        return db.execute("SELECT 1").fetchone()[0] == 1


def insert_iot_reading(values: dict[str, Any], timestamp: str | None = None) -> dict[str, Any]:
    timestamp = timestamp or utc_now()
    with connect() as db:
        cursor = db.execute(
            "INSERT INTO iot_readings(timestamp,temperature,humidity,electricity,water,occupancy,source,classification) VALUES(?,?,?,?,?,?,?, 'actual_iot')",
            (timestamp, values.get("temperature"), values.get("humidity"), values.get("electricity"),
             values.get("water"), values.get("occupancy"), "ESP32_IoT"),
        )
        row_id = cursor.lastrowid
        if row_id is None:
            raise RuntimeError("SQLite did not return the IoT reading id")
    return {"id": int(row_id), "timestamp": timestamp, **values, "source": "ESP32_IoT", "classification": "actual_iot"}


def latest_iot_reading() -> dict[str, Any] | None:
    with connect() as db:
        row = db.execute("SELECT * FROM iot_readings ORDER BY id DESC LIMIT 1").fetchone()
    return dict(row) if row else None


def list_iot_readings(*, limit: int = 100) -> list[dict[str, Any]]:
    limit = max(1, min(int(limit), 500))
    with connect() as db:
        rows = db.execute("SELECT * FROM iot_readings ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [dict(row) for row in rows]


def legacy_sensor_readings(*, actual_only: bool = False, limit: int = 100) -> list[dict[str, Any]]:
    limit = max(1, min(int(limit), 500))
    with connect() as db:
        tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "sensor_readings" not in tables:
            return []
        where = " WHERE COALESCE(source,'simulation') != 'simulation'" if actual_only else ""
        rows = db.execute(
            f"SELECT id,timestamp,temperature,humidity,electricity,water,occupancy,source FROM sensor_readings{where} ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    result = []
    for row in rows:
        item = dict(row)
        item["classification"] = "actual_iot" if item.get("source") not in {None, "simulation"} else "synthetic_legacy"
        result.append(item)
    return result
