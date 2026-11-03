from __future__ import annotations

import database
from services.weather import OpenMeteoService


def weather_fixture():
    return {"timezone": "Asia/Kolkata", "current": {"time": "2026-11-03T10:00", "temperature_2m": 29.5,
            "relative_humidity_2m": 60, "apparent_temperature": 30, "dew_point_2m": 20, "pressure_msl": 1012,
            "wind_speed_10m": 12, "wind_direction_10m": 90, "wind_gusts_10m": 18, "cloud_cover": 30,
            "precipitation": 0, "weather_code": 2, "visibility": 12000, "uv_index": 7, "is_day": 1},
            "hourly": {"time": ["2026-11-03T10:00"], "temperature_2m": [29.5], "relative_humidity_2m": [60],
                       "dew_point_2m": [20], "apparent_temperature": [30], "pressure_msl": [1012],
                       "wind_speed_10m": [12], "wind_direction_10m": [90], "wind_gusts_10m": [18],
                       "cloud_cover": [30], "precipitation": [0], "precipitation_probability": [65],
                       "weather_code": [2], "visibility": [12000], "uv_index": [7]},
            "daily": {"time": ["2026-11-03"], "temperature_2m_max": [31], "temperature_2m_min": [22],
                      "precipitation_sum": [1], "precipitation_probability_max": [65], "wind_speed_10m_max": [18],
                      "wind_gusts_10m_max": [24], "uv_index_max": [8], "sunrise": ["2026-11-03T06:10"],
                      "sunset": ["2026-11-03T17:45"], "weather_code": [61]}}


def air_fixture():
    return {"timezone": "Asia/Kolkata", "current": {"time": "2026-11-03T10:00", "pm2_5": 42.2, "pm10": 49,
            "us_aqi": 87, "european_aqi": 52, "dust": 3, "ozone": 50, "nitrogen_dioxide": 10,
            "sulphur_dioxide": 5, "carbon_monoxide": 400},
            "hourly": {"time": ["2026-11-03T10:00"], "pm2_5": [42.2], "pm10": [49], "us_aqi": [87],
                       "european_aqi": [52], "dust": [3], "ozone": [50], "nitrogen_dioxide": [10],
                       "sulphur_dioxide": [5], "carbon_monoxide": [400]}}


def test_weather_mapping_preserves_times_and_labels(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DATABASE_PATH", tmp_path / "weather.db")
    database.initialize_database()
    service = OpenMeteoService(fetch_json=lambda _url, _params: weather_fixture())
    current = service.current()
    assert current["success"] is True
    assert current["source"] == "Open-Meteo Forecast API"
    assert current["classification"] == "forecast"
    assert current["data"]["current"]["condition"] == "Partly cloudy"
    assert current["data"]["current"]["sunrise"] == "2026-11-03T06:10"
    assert current["data"]["current"]["visibility_m"] == 12000


def test_air_quality_is_always_marked_as_forecast_estimate(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DATABASE_PATH", tmp_path / "air.db")
    database.initialize_database()
    service = OpenMeteoService(fetch_json=lambda _url, _params: air_fixture())
    payload = service.air_quality()
    assert payload["success"] is True
    assert payload["classification"] == "forecast_estimate"
    assert payload["data"]["current"]["pm2_5_ugm3"] == 42.2
    assert payload["data"]["current"]["us_aqi"] == 87


def test_failure_returns_last_snapshot_as_stale(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DATABASE_PATH", tmp_path / "stale.db")
    database.initialize_database()
    service = OpenMeteoService(fetch_json=lambda _url, _params: weather_fixture())
    first = service.forecast()
    assert first["success"] is True
    service._cache["weather"] = (0.0, first)
    service.fetch_json = lambda _url, _params: (_ for _ in ()).throw(RuntimeError("offline"))
    stale = service.forecast()
    assert stale["success"] is True
    assert stale["stale"] is True
    assert "offline" in stale["stale_error"]


def test_no_stale_data_means_unavailable_not_random_values(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DATABASE_PATH", tmp_path / "offline.db")
    database.initialize_database()
    service = OpenMeteoService(fetch_json=lambda _url, _params: (_ for _ in ()).throw(RuntimeError("offline")))
    result = service.current()
    assert result["success"] is False
    assert result["classification"] == "unavailable"
    assert result["data"] is None
