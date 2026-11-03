"""Cached, validated Open-Meteo weather and air-quality forecast client."""
from __future__ import annotations

import copy
import json
import math
import threading
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from database import latest_weather_snapshot, save_weather_snapshot, utc_now

LATITUDE = 19.9501
LONGITUDE = 79.2993
TIMEZONE = "Asia/Kolkata"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
AIR_QUALITY_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"

WEATHER_CURRENT = (
    "temperature_2m,relative_humidity_2m,apparent_temperature,dew_point_2m,"
    "pressure_msl,wind_speed_10m,wind_direction_10m,wind_gusts_10m,cloud_cover,"
    "precipitation,weather_code,visibility,uv_index,is_day"
)
WEATHER_HOURLY = (
    "temperature_2m,relative_humidity_2m,dew_point_2m,apparent_temperature,"
    "pressure_msl,wind_speed_10m,wind_direction_10m,wind_gusts_10m,cloud_cover,"
    "precipitation,precipitation_probability,weather_code,visibility,uv_index"
)
WEATHER_DAILY = (
    "temperature_2m_max,temperature_2m_min,precipitation_sum,"
    "precipitation_probability_max,wind_speed_10m_max,wind_gusts_10m_max,"
    "uv_index_max,sunrise,sunset,weather_code"
)
AQ_VARIABLES = (
    "pm2_5,pm10,us_aqi,european_aqi,dust,ozone,nitrogen_dioxide,"
    "sulphur_dioxide,carbon_monoxide"
)


def _finite_number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if math.isfinite(number) else None


def _series_rows(group: Any, *, time_key: str = "time") -> list[dict[str, Any]]:
    if not isinstance(group, dict) or not isinstance(group.get(time_key), list):
        return []
    times = group[time_key]
    keys = [key for key, values in group.items() if key != time_key and isinstance(values, list)]
    rows: list[dict[str, Any]] = []
    for index, stamp in enumerate(times):
        if not isinstance(stamp, str):
            continue
        row: dict[str, Any] = {"time": stamp}
        for key in keys:
            values = group[key]
            value = values[index] if index < len(values) else None
            row[key] = value if isinstance(value, str) else _finite_number(value)
        if "weather_code" in row:
            row["condition"] = _weather_condition(row["weather_code"])
        rows.append(row)
    return rows


def _weather_condition(value: Any) -> str:
    code = _finite_number(value)
    if code is None:
        return "Unavailable"
    labels = {
        0: "Clear", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
        45: "Fog", 48: "Rime fog", 51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
        56: "Freezing drizzle", 57: "Dense freezing drizzle", 61: "Light rain", 63: "Moderate rain",
        65: "Heavy rain", 66: "Freezing rain", 67: "Heavy freezing rain", 71: "Light snow",
        73: "Moderate snow", 75: "Heavy snow", 77: "Snow grains", 80: "Light rain showers",
        81: "Moderate rain showers", 82: "Violent rain showers", 85: "Snow showers", 86: "Heavy snow showers",
        95: "Thunderstorm", 96: "Thunderstorm with hail", 99: "Severe thunderstorm with hail",
    }
    return labels.get(int(code), "Unknown weather code")


def _weather_current(raw: dict[str, Any]) -> dict[str, Any]:
    current = raw.get("current")
    if not isinstance(current, dict) or not isinstance(current.get("time"), str):
        raise ValueError("Open-Meteo weather response did not contain current conditions")
    daily = _series_rows(raw.get("daily"))
    day = daily[0] if daily else {}
    mapping = {
        "temperature_c": "temperature_2m",
        "feels_like_c": "apparent_temperature",
        "humidity_pct": "relative_humidity_2m",
        "dew_point_c": "dew_point_2m",
        "pressure_hpa": "pressure_msl",
        "wind_speed_kmh": "wind_speed_10m",
        "wind_direction_deg": "wind_direction_10m",
        "wind_gusts_kmh": "wind_gusts_10m",
        "cloud_cover_pct": "cloud_cover",
        "precipitation_mm": "precipitation",
        "weather_code": "weather_code",
        "visibility_m": "visibility",
        "uv_index": "uv_index",
        "is_day": "is_day",
    }
    result: dict[str, Any] = {"time": current["time"]}
    for target, source in mapping.items():
        value = current.get(source)
        result[target] = bool(value) if target == "is_day" and value is not None else _finite_number(value)
    result["condition"] = _weather_condition(current.get("weather_code"))
    result["sunrise"] = day.get("sunrise")
    result["sunset"] = day.get("sunset")
    return result


def _air_current(raw: dict[str, Any]) -> dict[str, Any]:
    current = raw.get("current")
    if isinstance(current, dict) and isinstance(current.get("time"), str):
        source = current
        stamp = current["time"]
    else:
        hourly = raw.get("hourly")
        if not isinstance(hourly, dict):
            raise ValueError("Open-Meteo air-quality response contains no hourly forecast")
        times = hourly.get("time")
        if not isinstance(times, list) or not times:
            raise ValueError("Open-Meteo air-quality response contains no forecast times")
        now_local = datetime.now(timezone.utc).astimezone(ZoneInfo(TIMEZONE)).replace(tzinfo=None)
        chosen = 0
        for index, time_text in enumerate(times):
            if not isinstance(time_text, str):
                continue
            try:
                candidate = datetime.fromisoformat(time_text)
            except ValueError:
                continue
            if candidate <= now_local:
                chosen = index
            else:
                break
        source = {
            name: values[chosen]
            for name, values in hourly.items()
            if name != "time" and isinstance(values, list) and chosen < len(values)
        }
        stamp = times[chosen]
    aliases = {
        "pm2_5_ugm3": "pm2_5", "pm10_ugm3": "pm10", "us_aqi": "us_aqi",
        "european_aqi": "european_aqi", "dust_ugm3": "dust",
        "ozone_ugm3": "ozone", "nitrogen_dioxide_ugm3": "nitrogen_dioxide",
        "sulphur_dioxide_ugm3": "sulphur_dioxide", "carbon_monoxide_ugm3": "carbon_monoxide",
    }
    result: dict[str, Any] = {"time": stamp}
    for target, key in aliases.items():
        result[target] = _finite_number(source.get(key))
    return result


class OpenMeteoService:
    """A small process cache plus persistent last-successful snapshots for outages."""

    def __init__(self, *, ttl_seconds: int = 600, air_ttl_seconds: int = 900,
                 fetch_json: Callable[[str, dict[str, str]], dict[str, Any]] | None = None) -> None:
        self.ttl_seconds = ttl_seconds
        self.air_ttl_seconds = air_ttl_seconds
        self.fetch_json = fetch_json or self._fetch_json
        self._lock = threading.RLock()
        self._cache: dict[str, tuple[float, dict[str, Any]]] = {}

    @staticmethod
    def _fetch_json(base_url: str, params: dict[str, str]) -> dict[str, Any]:
        url = f"{base_url}?{urlencode(params)}"
        request = Request(url, headers={"User-Agent": "RCERT-Smart-Campus/2.0 (educational project)", "Accept": "application/json"})
        try:
            with urlopen(request, timeout=10) as response:
                if response.status != 200:
                    raise RuntimeError(f"Open-Meteo returned HTTP {response.status}")
                parsed = json.loads(response.read(2_000_000).decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Open-Meteo request failed: {exc}") from exc
        if not isinstance(parsed, dict) or parsed.get("error"):
            detail = parsed.get("reason", "invalid JSON response") if isinstance(parsed, dict) else "invalid JSON response"
            raise RuntimeError(f"Open-Meteo response error: {detail}")
        return parsed

    def _params_weather(self) -> dict[str, str]:
        return {
            "latitude": str(LATITUDE), "longitude": str(LONGITUDE), "timezone": TIMEZONE,
            "temperature_unit": "celsius", "wind_speed_unit": "kmh", "precipitation_unit": "mm",
            "current": WEATHER_CURRENT, "hourly": WEATHER_HOURLY, "daily": WEATHER_DAILY,
            "forecast_days": "7", "forecast_hours": "168",
        }

    def _params_air(self) -> dict[str, str]:
        return {
            "latitude": str(LATITUDE), "longitude": str(LONGITUDE), "timezone": TIMEZONE,
            "current": AQ_VARIABLES, "hourly": AQ_VARIABLES, "forecast_days": "5",
        }

    def _load(self, kind: str) -> dict[str, Any]:
        ttl = self.air_ttl_seconds if kind == "air_quality" else self.ttl_seconds
        with self._lock:
            entry = self._cache.get(kind)
            if entry and time.monotonic() - entry[0] < ttl:
                return copy.deepcopy(entry[1])
            base_url = AIR_QUALITY_URL if kind == "air_quality" else WEATHER_URL
            params = self._params_air() if kind == "air_quality" else self._params_weather()
            try:
                raw = self.fetch_json(base_url, params)
                if kind == "air_quality":
                    current = _air_current(raw)
                    hourly = _series_rows(raw.get("hourly"))
                    data = {"current": current, "hourly": hourly, "timezone": raw.get("timezone", TIMEZONE)}
                    source = "Open-Meteo Air Quality API (CAMS forecast)"
                    classification = "forecast_estimate"
                else:
                    current = _weather_current(raw)
                    hourly = _series_rows(raw.get("hourly"))
                    daily = _series_rows(raw.get("daily"))
                    data = {"current": current, "hourly": hourly, "daily": daily, "timezone": raw.get("timezone", TIMEZONE)}
                    source = "Open-Meteo Forecast API"
                    classification = "forecast"
                payload = {
                    "success": True,
                    "source": source,
                    "classification": classification,
                    "location": {"name": "RCERT, Chandrapur", "latitude": LATITUDE, "longitude": LONGITUDE, "timezone": TIMEZONE},
                    "fetched_at": utc_now(),
                    "stale": False,
                    "attribution": "Weather and air-quality forecast data by Open-Meteo.com",
                    "data": data,
                }
                try:
                    save_weather_snapshot(kind, payload, payload["fetched_at"])
                except Exception:
                    # The API remains useful during a database write outage.
                    pass
                self._cache[kind] = (time.monotonic(), payload)
                return copy.deepcopy(payload)
            except Exception as exc:
                stale_payload: dict[str, Any] | None = None
                if entry:
                    stale_payload = copy.deepcopy(entry[1])
                else:
                    try:
                        snapshot = latest_weather_snapshot(kind)
                        if snapshot:
                            stale_payload = copy.deepcopy(snapshot["payload"])
                    except Exception:
                        stale_payload = None
                if stale_payload:
                    stale_payload["stale"] = True
                    stale_payload["stale_error"] = str(exc)
                    retry_window = min(ttl, 60)
                    self._cache[kind] = (time.monotonic() - ttl + retry_window, stale_payload)
                    return copy.deepcopy(stale_payload)
                unavailable = {
                    "success": False,
                    "source": "Open-Meteo",
                    "classification": "unavailable",
                    "location": {"name": "RCERT, Chandrapur", "latitude": LATITUDE, "longitude": LONGITUDE, "timezone": TIMEZONE},
                    "fetched_at": None,
                    "stale": False,
                    "error": str(exc),
                    "data": None,
                }
                retry_window = min(ttl, 60)
                self._cache[kind] = (time.monotonic() - ttl + retry_window, unavailable)
                return copy.deepcopy(unavailable)

    def current(self) -> dict[str, Any]:
        full = self._load("weather")
        if full.get("success") and isinstance(full.get("data"), dict):
            return {**full, "data": {"current": full["data"].get("current"), "timezone": TIMEZONE}}
        return full

    def forecast(self) -> dict[str, Any]:
        full = self._load("weather")
        if full.get("success") and isinstance(full.get("data"), dict):
            return {**full, "data": {"hourly": full["data"].get("hourly", []), "daily": full["data"].get("daily", []), "timezone": TIMEZONE}}
        return full

    def air_quality(self) -> dict[str, Any]:
        return self._load("air_quality")


weather_service = OpenMeteoService()
