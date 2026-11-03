from __future__ import annotations

import database
from application import app, weather_service
from tests.test_api import _weather_fixture, _air_fixture


def _client(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DATABASE_PATH", tmp_path / "v2-test.db")
    database.initialize_database()
    weather_service._cache.clear()
    monkeypatch.setattr(weather_service, "fetch_json", lambda url, params: _air_fixture() if "air-quality" in url else _weather_fixture())
    return app.test_client()


def test_settings_get_and_post(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    res = client.get("/api/settings")
    assert res.status_code == 200
    assert res.json["success"] is True
    assert res.json["settings"]["temperature_unit"] == "celsius"

    post_res = client.post("/api/settings", json={"temperature_unit": "fahrenheit", "theme": "dark"})
    assert post_res.status_code == 200
    assert post_res.json["settings"]["temperature_unit"] == "fahrenheit"

    # Verify persistent get
    check = client.get("/api/settings")
    assert check.json["settings"]["temperature_unit"] == "fahrenheit"


def test_reports_endpoints(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    
    # Reports summary
    summary = client.get("/api/reports/summary")
    assert summary.status_code == 200
    assert summary.json["success"] is True
    assert summary.json["total_zones"] == 18
    assert "daily_forecast" in summary.json

    # CSV exports
    weather_csv = client.get("/api/reports/weather.csv")
    assert weather_csv.status_code == 200
    assert "text/csv" in weather_csv.content_type
    assert b"temperature_2m" in weather_csv.data

    air_csv = client.get("/api/reports/air-quality.csv")
    assert air_csv.status_code == 200
    assert "text/csv" in air_csv.content_type
    assert b"pm2_5" in air_csv.data

    alerts_csv = client.get("/api/reports/alerts.csv")
    assert alerts_csv.status_code == 200
    assert "text/csv" in alerts_csv.content_type
    assert b"severity" in alerts_csv.data


def test_historical_analytics(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    # Trigger a weather call so a snapshot is saved
    client.get("/api/weather/current")
    hist = client.get("/api/analytics/historical")
    assert hist.status_code == 200
    assert hist.json["success"] is True
    assert "history" in hist.json
