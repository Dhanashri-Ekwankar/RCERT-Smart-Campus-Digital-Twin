from __future__ import annotations

from datetime import datetime, timezone

import database
from application import app, weather_service


def _weather_fixture():
    return {
        "timezone": "Asia/Kolkata",
        "current": {"time": "2026-11-03T10:00", "temperature_2m": 29.5, "relative_humidity_2m": 60,
                    "apparent_temperature": 30, "dew_point_2m": 20, "pressure_msl": 1012,
                    "wind_speed_10m": 12, "wind_direction_10m": 90, "wind_gusts_10m": 18,
                    "cloud_cover": 30, "precipitation": 0, "weather_code": 2,
                    "visibility": 12000, "uv_index": 7, "is_day": 1},
        "hourly": {"time": ["2026-11-03T10:00", "2026-11-03T11:00"], "temperature_2m": [29.5, 30],
                   "relative_humidity_2m": [60, 58], "dew_point_2m": [20, 20],
                   "apparent_temperature": [30, 31], "pressure_msl": [1012, 1011],
                   "wind_speed_10m": [12, 14], "wind_direction_10m": [90, 95],
                   "wind_gusts_10m": [18, 20], "cloud_cover": [30, 35], "precipitation": [0, 1],
                   "precipitation_probability": [20, 65], "weather_code": [2, 61],
                   "visibility": [12000, 9000], "uv_index": [7, 8]},
        "daily": {"time": ["2026-11-03"], "temperature_2m_max": [31], "temperature_2m_min": [22],
                  "precipitation_sum": [1], "precipitation_probability_max": [65], "wind_speed_10m_max": [18],
                  "wind_gusts_10m_max": [24], "uv_index_max": [8], "sunrise": ["2026-11-03T06:10"],
                  "sunset": ["2026-11-03T17:45"], "weather_code": [61]},
    }


def _air_fixture():
    return {"timezone": "Asia/Kolkata", "current": {"time": "2026-11-03T10:00", "pm2_5": 42.2, "pm10": 49,
            "us_aqi": 87, "european_aqi": 52, "dust": 3, "ozone": 50, "nitrogen_dioxide": 10,
            "sulphur_dioxide": 5, "carbon_monoxide": 400},
            "hourly": {"time": ["2026-11-03T10:00"], "pm2_5": [42.2], "pm10": [49], "us_aqi": [87],
                       "european_aqi": [52], "dust": [3], "ozone": [50], "nitrogen_dioxide": [10],
                       "sulphur_dioxide": [5], "carbon_monoxide": [400]}}


def _isolate(client_fixture, tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DATABASE_PATH", tmp_path / "api-test.db")
    database.initialize_database()
    weather_service._cache.clear()
    return app.test_client()


def test_health_home_campus_and_legacy_aliases(tmp_path, monkeypatch):
    client = _isolate(None, tmp_path, monkeypatch)
    assert client.get("/").status_code == 200
    assert client.get("/api/health").json["database"]["available"] is True
    assert client.get("/api/campus").json["campus"]["classification"] == "verified_institutional_info"
    zones = client.get("/api/campus/zones").json["zones"]
    assert len(zones) == 18
    assert client.get("/api/campus-zones").json["zones"] == zones


def test_weather_routes_use_open_meteo_and_are_cached(tmp_path, monkeypatch):
    client = _isolate(None, tmp_path, monkeypatch)
    calls = []
    def fake_fetch(url, params):
        calls.append(url)
        return _air_fixture() if "air-quality" in url else _weather_fixture()
    monkeypatch.setattr(weather_service, "fetch_json", fake_fetch)
    current = client.get("/api/weather/current")
    assert current.status_code == 200
    body = current.json
    assert body["source"] == "Open-Meteo Forecast API"
    assert body["classification"] == "forecast"
    assert body["data"]["current"]["condition"] == "Partly cloudy"
    forecast = client.get("/api/weather/forecast").json
    assert len(forecast["data"]["hourly"]) == 2
    assert forecast["data"]["daily"][0]["sunrise"] == "2026-11-03T06:10"
    assert len(calls) == 1


def test_weather_failure_shows_unavailable_instead_of_inventing_values(tmp_path, monkeypatch):
    client = _isolate(None, tmp_path, monkeypatch)
    def fail(_url, _params):
        raise RuntimeError("test network failure")
    monkeypatch.setattr(weather_service, "fetch_json", fail)
    response = client.get("/api/weather/current")
    assert response.status_code == 503
    assert response.json["success"] is False
    assert response.json["data"] is None
    assert response.json["classification"] == "unavailable"


def test_iot_input_rejects_nan_and_simulation_is_disabled(tmp_path, monkeypatch):
    client = _isolate(None, tmp_path, monkeypatch)
    bad = client.post("/api/iot-data", json={"temperature": "nan", "humidity": 50})
    assert bad.status_code == 400
    assert client.post("/api/simulate-reading").status_code == 410
    saved = client.post("/api/iot-data", json={"temperature": 27.5})
    assert saved.status_code == 201
    assert saved.json["classification"] == "actual_iot"
    assert saved.json["data"]["temperature"] == 27.5
    assert "humidity" not in saved.json["data"]
    assert "electricity" not in saved.json["data"]


def test_vision_event_ingest_validates_and_suppresses_duplicate_crossings(tmp_path, monkeypatch):
    client = _isolate(None, tmp_path, monkeypatch)
    timestamp = datetime.now(timezone.utc).isoformat()
    payload = {"camera_id": "local-webcam", "zone_id": "main_gate", "session_id": "session-a",
               "track_id": "track-1", "event_type": "entry", "direction": "entry", "occurred_at": timestamp}
    first = client.post("/api/vision/events", json=payload)
    assert first.status_code == 201
    second_payload = {**payload, "event_id": "retry-2"}
    second = client.post("/api/vision/events", json=second_payload)
    assert second.status_code == 200 and second.json["duplicate"] is True
    assert client.get("/api/vision/summary").json["total_events"] == 1
    rejected = client.post("/api/vision/events", json={**payload, "face_image": "no"})
    assert rejected.status_code == 400


def test_vision_configuration_is_validated_and_persisted(tmp_path, monkeypatch):
    client = _isolate(None, tmp_path, monkeypatch)
    payload = {"camera_id": "local-webcam", "zone_id": "main_gate", "confidence": 0.6,
               "line": {"start": [0.2, 0.5], "end": [0.8, 0.5]}, "entry_direction": "left_to_right"}
    saved = client.post("/api/vision/config", json=payload)
    assert saved.status_code == 200
    loaded = client.get("/api/vision/config/local-webcam")
    assert loaded.status_code == 200
    assert loaded.json["config"]["line"] == payload["line"]
    assert client.post("/api/vision/config", json={**payload, "confidence": 1.5}).status_code == 400


def test_alert_acknowledge_and_resolve_endpoints_persist(tmp_path, monkeypatch):
    client = _isolate(None, tmp_path, monkeypatch)
    alert_id = database.upsert_alert(category="weather", severity="warning", title="Rain soon", message="65%", source="Open-Meteo", support={"value": 65}, dedupe_key="test-rain")
    ack = client.post(f"/api/alerts/{alert_id}/acknowledge")
    assert ack.status_code == 200 and ack.json["alert"]["acknowledged_at"]
    resolved = client.post(f"/api/alerts/{alert_id}/resolve")
    assert resolved.status_code == 200 and resolved.json["alert"]["resolved_at"]
    assert client.get("/api/alerts?state=resolved").json["count"] == 1
