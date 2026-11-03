from __future__ import annotations

import database


def test_initialize_database_preserves_legacy_sensor_rows(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DATABASE_PATH", tmp_path / "campus.db")
    with database.connect() as db:
        db.execute("CREATE TABLE sensor_readings (id INTEGER PRIMARY KEY, timestamp TEXT NOT NULL, temperature REAL NOT NULL, humidity REAL NOT NULL, electricity REAL NOT NULL, water REAL NOT NULL, occupancy REAL NOT NULL, source TEXT DEFAULT 'simulation')")
        db.execute("INSERT INTO sensor_readings(timestamp,temperature,humidity,electricity,water,occupancy,source) VALUES('2026-09-01 10:00:00',27,55,10,20,30,'simulation')")
    database.initialize_database()
    database.initialize_database()
    with database.connect() as db:
        count = db.execute("SELECT COUNT(*) FROM sensor_readings").fetchone()[0]
        tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert count == 1
    assert {"weather_snapshots", "vision_events", "alerts", "cameras", "camera_config"}.issubset(tables)


def test_alert_acknowledgement_and_resolution_are_persistent(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DATABASE_PATH", tmp_path / "campus.db")
    database.initialize_database()
    alert_id = database.upsert_alert(category="weather", severity="warning", title="Rain", message="Rain chance", source="Open-Meteo", support={"value": 75}, dedupe_key="rain-1")
    acknowledged = database.change_alert_state(alert_id, "acknowledge")
    assert acknowledged and acknowledged["acknowledged_at"]
    resolved = database.change_alert_state(alert_id, "resolve")
    assert resolved and resolved["resolved_at"] and resolved["acknowledged_at"]
    assert database.list_alerts(state="resolved")[0]["id"] == alert_id


def test_camera_configuration_round_trips(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DATABASE_PATH", tmp_path / "campus.db")
    database.initialize_database()
    config = database.save_camera_config(camera_id="local-webcam", zone_id="main_gate", line={"start": [0.2, 0.5], "end": [0.8, 0.5]}, entry_direction="left_to_right", confidence=0.6)
    loaded = database.get_camera_config("local-webcam")
    assert loaded is not None
    assert loaded == config
    assert loaded["line"]["start"] == [0.2, 0.5]
