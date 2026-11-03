"""Real-event analytics. Synthetic legacy sensor records are never included."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from typing import Any

import database

LOCAL_TZ = ZoneInfo("Asia/Kolkata")


def _parse_instant(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def resolve_range(period: str = "today", since: str | None = None, until: str | None = None) -> tuple[str, str]:
    now = datetime.now(LOCAL_TZ)
    if since or until:
        end = _parse_instant(until) if until else now.astimezone(timezone.utc)
        if end is None:
            raise ValueError("Invalid analytics end time")
        start = _parse_instant(since) if since else end - timedelta(days=7)
        if not start or start > end:
            raise ValueError("Invalid analytics time range")
        return start.isoformat(timespec="seconds").replace("+00:00", "Z"), end.isoformat(timespec="seconds").replace("+00:00", "Z")
    local_now = now
    if period == "today":
        start_local = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "yesterday":
        start_local = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
        local_now = start_local + timedelta(days=1)
    elif period == "7d":
        start_local = now - timedelta(days=7)
    elif period == "30d":
        start_local = now - timedelta(days=30)
    else:
        raise ValueError("period must be today, yesterday, 7d, or 30d")
    return start_local.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"), local_now.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def footfall(*, period: str = "today", since: str | None = None, until: str | None = None,
             camera_id: str | None = None) -> dict[str, Any]:
    start, end = resolve_range(period, since, until)
    events = database.list_vision_events(camera_id=camera_id, since=start, until=end, limit=1000)
    buckets: dict[str, dict[str, int]] = defaultdict(lambda: {"entries": 0, "exits": 0})
    totals = {"entries": 0, "exits": 0}
    by_camera: dict[str, dict[str, int]] = defaultdict(lambda: {"entries": 0, "exits": 0})
    for event in events:
        instant = _parse_instant(event.get("occurred_at"))
        if not instant:
            continue
        local = instant.astimezone(LOCAL_TZ)
        bucket = local.strftime("%Y-%m-%d %H:00") if period in {"today", "yesterday"} and not (since or until) else local.strftime("%Y-%m-%d")
        kind = event.get("event_type")
        if kind not in totals:
            continue
        bucket_key = "entries" if kind == "entry" else "exits"
        totals[bucket_key] += 1
        buckets[bucket][bucket_key] += 1
        by_camera[event.get("camera_id", "unknown")][bucket_key] += 1
    timeline = [{"time": key, **value} for key, value in sorted(buckets.items())]
    return {
        "success": True,
        "classification": "actual_camera",
        "source": "validated anonymous camera events",
        "fetched_at": database.utc_now(),
        "range": {"since": start, "until": end, "period": period},
        "has_data": bool(events),
        "entries": totals["entries"],
        "exits": totals["exits"],
        "net_flow": totals["entries"] - totals["exits"],
        "timeline": timeline,
        "by_camera": [{"camera_id": key, **counts} for key, counts in sorted(by_camera.items())],
    }


def _parse_forecast_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    # Open-Meteo returns local wall-clock timestamps when timezone is requested.
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=LOCAL_TZ)
    return parsed.astimezone(LOCAL_TZ)


def weather_insights(forecast: dict[str, Any], air_quality: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Produce comprehensive, threshold-based observations backed by supplied forecast values."""
    if not isinstance(forecast, dict) or not forecast.get("success"):
        return []
    data = forecast.get("data") or {}
    hourly = data.get("hourly") or []
    daily = data.get("daily") or []
    now = datetime.now(LOCAL_TZ)
    next_hours: list[dict[str, Any]] = []
    for row in hourly:
        stamp = _parse_forecast_time(row.get("time"))
        if stamp and now <= stamp <= now + timedelta(hours=8):
            next_hours.append(row)
    if not next_hours and hourly:
        next_hours = hourly[:8]

    insights: list[dict[str, Any]] = []

    # 1. Rain probability
    rain = [(_parse_forecast_time(row.get("time")), row.get("precipitation_probability")) for row in next_hours]
    rain = [(stamp, value) for stamp, value in rain if isinstance(value, (int, float))]
    if rain:
        stamp, value = max(rain, key=lambda pair: pair[1])
        if value >= 50:
            insights.append({
                "category": "weather", "severity": "warning" if value >= 70 else "info",
                "title": "Precipitation forecast",
                "message": f"Precipitation probability reaches {round(value)}% in the near-term forecast window.",
                "value": round(value), "unit": "%",
                "time_window": stamp.astimezone(LOCAL_TZ).isoformat() if stamp else None,
                "source": forecast.get("source", "Open-Meteo"), "classification": "forecast"
            })

    # 2. High Temperature / Heat Index
    temps = [(_parse_forecast_time(row.get("time")), row.get("temperature_2m"), row.get("apparent_temperature")) for row in next_hours]
    temps = [(s, t, a) for s, t, a in temps if isinstance(t, (int, float))]
    if temps:
        stamp, max_temp, max_apparent = max(temps, key=lambda p: p[1])
        if max_temp >= 35.0 or (isinstance(max_apparent, (int, float)) and max_apparent >= 38.0):
            insights.append({
                "category": "temperature", "severity": "warning",
                "title": "Elevated campus temperature",
                "message": f"Forecast temperature peaks at {max_temp:.1f}°C (feels like {max_apparent or max_temp:.1f}°C). Hydration recommended.",
                "value": round(max_temp, 1), "unit": "°C",
                "time_window": stamp.astimezone(LOCAL_TZ).isoformat() if stamp else None,
                "source": forecast.get("source", "Open-Meteo"), "classification": "forecast"
            })
        elif max_temp <= 16.0:
            insights.append({
                "category": "temperature", "severity": "info",
                "title": "Cool temperature forecast",
                "message": f"Forecast indicates temperatures dropping to {max_temp:.1f}°C.",
                "value": round(max_temp, 1), "unit": "°C",
                "time_window": stamp.astimezone(LOCAL_TZ).isoformat() if stamp else None,
                "source": forecast.get("source", "Open-Meteo"), "classification": "forecast"
            })

    # 3. UV Index
    uv_days = [(row.get("date") or row.get("time"), row.get("uv_index_max")) for row in daily]
    uv_days = [(date, value) for date, value in uv_days if isinstance(value, (int, float))]
    if uv_days:
        date, value = max(uv_days, key=lambda pair: pair[1])
        if value >= 7.0:
            insights.append({
                "category": "uv", "severity": "warning" if value >= 8.0 else "info",
                "title": "High solar UV exposure",
                "message": f"Peak forecast UV index is {value:g}. Sun protection advised during midday hours.",
                "value": value, "unit": "UV index", "time_window": str(date),
                "source": forecast.get("source", "Open-Meteo"), "classification": "forecast"
            })

    # 4. Wind & Gusts
    gusts = [(_parse_forecast_time(row.get("time")), row.get("wind_gusts_10m")) for row in next_hours]
    gusts = [(stamp, value) for stamp, value in gusts if isinstance(value, (int, float))]
    if gusts:
        stamp, value = max(gusts, key=lambda pair: pair[1])
        if value >= 35.0:
            insights.append({
                "category": "wind", "severity": "warning" if value >= 50.0 else "info",
                "title": "Strong wind gusts forecast",
                "message": f"Forecast surface gusts may reach {value:g} km/h.",
                "value": value, "unit": "km/h",
                "time_window": stamp.astimezone(LOCAL_TZ).isoformat() if stamp else None,
                "source": forecast.get("source", "Open-Meteo"), "classification": "forecast"
            })

    # 5. Air Quality
    aq = (air_quality or {}).get("data", {}).get("current", {}) if isinstance(air_quality, dict) else {}
    aqi = aq.get("us_aqi")
    pm25 = aq.get("pm2_5_ugm3")
    if isinstance(aqi, (int, float)) and aqi >= 101:
        severity = "critical" if aqi >= 201 else "warning"
        insights.append({
            "category": "air_quality", "severity": severity,
            "title": "Elevated particulate / AQI estimate",
            "message": f"CAMS air-quality model projects US AQI of {round(aqi)} (PM2.5: {pm25 or 'N/A'} µg/m³). Model estimate.",
            "value": round(aqi), "unit": "US AQI", "time_window": aq.get("time"),
            "source": (air_quality or {}).get("source", "Open-Meteo CAMS"), "classification": "forecast_estimate"
        })

    # 6. Outdoor Activity Suitability
    is_favorable = True
    reasons = []

    # Check precipitation likelihood from both current telemetry and upcoming forecast window
    curr = forecast.get("data", {}).get("current", {}) if isinstance(forecast, dict) else {}
    curr_rain_prob = curr.get("precipitation_probability")
    curr_rain_vol = curr.get("rain") or curr.get("precipitation")
    curr_code = curr.get("weather_code")

    max_rain_prob = 0
    if isinstance(curr_rain_prob, (int, float)):
        max_rain_prob = max(max_rain_prob, curr_rain_prob)
    if rain:
        max_rain_prob = max(max_rain_prob, max(v for _, v in rain))

    if max_rain_prob >= 35:
        is_favorable = False
        reasons.append(f"rain likelihood ({round(max_rain_prob)}% probability)")
    elif isinstance(curr_rain_vol, (int, float)) and curr_rain_vol > 0.2:
        is_favorable = False
        reasons.append(f"active rainfall ({curr_rain_vol:.1f} mm)")
    elif isinstance(curr_code, (int, float)) and int(curr_code) in (51, 53, 55, 61, 63, 65, 80, 81, 82, 95, 96, 99):
        is_favorable = False
        reasons.append("inclement precipitation conditions")

    if temps and any(t >= 37 for _, t, _ in temps):
        is_favorable = False
        reasons.append("high heat index (≥37°C)")

    if gusts and any(g >= 40 for _, g in gusts):
        is_favorable = False
        reasons.append("strong wind gusts (≥40 km/h)")

    if isinstance(aqi, (int, float)) and aqi >= 120:
        is_favorable = False
        reasons.append(f"poor air quality (AQI {round(aqi)})")

    # Stable day bucket prevents microsecond timestamp churn on alert deduplication
    suitability_stamp = now.astimezone(LOCAL_TZ).strftime("%Y-%m-%d")

    if is_favorable:
        insights.append({
            "category": "suitability", "severity": "info",
            "title": "Outdoor campus activity: Favorable",
            "message": "Current meteorological indicators are within normal seasonal comfort thresholds for RCERT campus.",
            "value": 1, "unit": "index", "time_window": suitability_stamp,
            "source": "RCERT Intelligence Engine", "classification": "derived_analytics"
        })
    else:
        insights.append({
            "category": "suitability", "severity": "warning",
            "title": "Outdoor campus activity: Caution",
            "message": f"Consider limiting prolonged outdoor campus activities due to {' and '.join(reasons)}.",
            "value": 0, "unit": "index", "time_window": suitability_stamp,
            "source": "RCERT Intelligence Engine", "classification": "derived_analytics"
        })

    return insights
