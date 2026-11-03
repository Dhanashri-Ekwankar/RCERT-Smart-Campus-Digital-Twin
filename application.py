"""RCERT Smart Campus Digital Twin — local, source-labeled Flask API."""
from __future__ import annotations

import csv
import io
import math
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, render_template, request, Response

import database
from database import DATABASE_PATH, initialize_database
from services import vision as vision_service
from services.analytics import footfall, weather_insights
from services.weather import weather_service

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 4 * 1024 * 1024
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.jinja_env.auto_reload = True

try:
    initialize_database()
except Exception:
    pass

CAMPUS = {
    "name": "Rajiv Gandhi College of Engineering, Research & Technology",
    "short_name": "RCERT", "city": "Chandrapur", "state": "Maharashtra", "country": "India",
    "latitude": 19.9501, "longitude": 79.2993, "timezone": "Asia/Kolkata",
    "official_url": "https://www.rcert.ac.in/", "established": 1983, "college_code": "4163",
    "geometry_classification": "conceptual", "classification": "verified_institutional_info",
    "source": "https://www.rcert.ac.in/", "retrieved_at": "2026-11-02",
}

CAMPUS_ZONES = [
    {
        "id": "boys_hostel", "name": "Boys Hostel", "type": "Hostel",
        "description": "On-campus residential facility for male undergraduate and polytechnic students, equipped with study halls, mess facility, and 24/7 security.",
        "facilities": ["Mess Hall", "Common Room", "Indoor Games", "Study Reading Room"]
    },
    {
        "id": "mba", "name": "MBA Department", "type": "Academic",
        "description": "Department of Management Studies offering Master of Business Administration with specializations in Finance, Marketing, HR, and Operations.",
        "facilities": ["Smart Classrooms", "Management Seminar Hall", "Case Study Discussion Rooms"]
    },
    {
        "id": "polytechnic", "name": "Polytechnic Wing", "type": "Academic",
        "description": "RCERT Polytechnic Wing delivering technical diploma programs in Civil, Mechanical, Electrical, and Mining Engineering approved by MSBTE.",
        "facilities": ["Applied Physics Lab", "Basic Electrical Workshop", "Drafting Hall"]
    },
    {
        "id": "mining", "name": "Mining Engineering", "type": "Academic",
        "description": "One of the flagship departments in Central India, located strategically in the Chandrapur coal belt with specialized labs for rock mechanics and mineral processing.",
        "facilities": ["Mine Ventilation Lab", "Rock Mechanics Lab", "Surveying & GIS Lab", "Geology Museum"]
    },
    {
        "id": "computer_science", "name": "Computer Science & Engineering", "type": "Academic",
        "description": "Established department delivering B.Tech & research programs in CSE. High-performance computing labs, software engineering suites, and cloud computing sandbox.",
        "facilities": ["Advanced Computing Lab", "Networking & Cyber Security Lab", "Software Dev Lab", "Open Source Lab"]
    },
    {
        "id": "civil", "name": "Civil Engineering", "type": "Academic",
        "description": "Department of Civil Engineering with comprehensive material testing, concrete technology, geotechnical, environmental, and structural testing laboratories.",
        "facilities": ["Strength of Materials Lab", "Geotechnical Engineering Lab", "Environmental Engineering Lab", "Highway Engineering Lab"]
    },
    {
        "id": "data_science", "name": "Data Science & AI", "type": "Academic",
        "description": "Cutting-edge department focused on Artificial Intelligence, Machine Learning, Deep Learning, Big Data Analytics, and Natural Language Processing.",
        "facilities": ["AI Research Workstations", "Big Data Analytics Lab", "Deep Learning GPU Cluster"]
    },
    {
        "id": "mechanical", "name": "Mechanical Engineering", "type": "Academic",
        "description": "Premier department featuring thermal engineering, CAD/CAM design center, internal combustion engine testing, and refrigeration research.",
        "facilities": ["CAD/CAM Center", "Fluid Mechanics Lab", "Heat Transfer Lab", "IC Engine Test Rig", "Dynamics of Machines Lab"]
    },
    {
        "id": "electrical", "name": "Electrical Engineering", "type": "Academic",
        "description": "Focuses on Power Systems, Electrical Machines, Power Electronics, Renewable Energy integration, and Microgrid design.",
        "facilities": ["Electrical Machines Lab", "Power System Simulator", "Control Systems Lab", "Power Electronics Lab"]
    },
    {
        "id": "electrical_workshop", "name": "Electrical Workshop", "type": "Workshop",
        "description": "Central fabrication, machining, fitting, welding, carpentry, and electrical wiring workshop for foundational practical engineering training.",
        "facilities": ["Machine Shop (Lathes/Milling)", "Welding Booths", "Foundry & Pattern Making", "Carpentry & Fitting"]
    },
    {
        "id": "auditorium", "name": "Auditorium", "type": "Facility",
        "description": "A 500+ seat acoustic auditorium hosting international conferences, technical symposiums, youth festivals, convocations, and guest lectures.",
        "facilities": ["Audio-Visual Projection System", "Acoustic Wall Treatment", "Green Rooms", "Central AC"]
    },
    {
        "id": "canteen", "name": "Kaka Canteen", "type": "Facility",
        "description": "Centrally located campus dining and refreshment hub serving wholesome hygienic vegetarian snacks, meals, and beverages for students and staff.",
        "facilities": ["Dining Hall", "Outdoor Seating Deck", "Hygienic Kitchen", "Beverage Counter"]
    },
    {
        "id": "gym", "name": "Gym", "type": "Facility",
        "description": "Dedicated fitness center equipped with modern strength training, cardio equipment, indoor badminton court, and table tennis.",
        "facilities": ["Cardio Zone", "Free Weights Area", "Table Tennis Arena", "Yoga & Aerobics Deck"]
    },
    {
        "id": "girls_hostel", "name": "Girls Hostel", "type": "Hostel",
        "description": "Secure, comfortable on-campus residential facility for female students with round-the-clock warden, dining mess, and recreation lounge.",
        "facilities": ["Private Dining Mess", "Recreation Hall", "Wi-Fi Study Lounge", "Security Desk"]
    },
    {
        "id": "boys_parking", "name": "Boys Parking", "type": "Parking",
        "description": "Designated shaded two-wheeler and four-wheeler parking zone for students and visitors near the south-west campus entry.",
        "facilities": ["Two-Wheeler Bays", "Covered Sheds", "Security Checkpoint"]
    },
    {
        "id": "girls_parking", "name": "Girls Parking", "type": "Parking",
        "description": "Designated secure parking bay adjacent to the administrative wing and girls hostel for female students and faculty.",
        "facilities": ["Designated Student Bays", "Covered Sheds", "Lighting & Surveillance"]
    },
    {
        "id": "main_building", "name": "RCERT Main Building", "type": "Administration",
        "description": "The administrative and academic headquarters housing the Principal's Office, Registrar, Central Library, Examination Cell, Accounts, and Boardroom.",
        "facilities": ["Principal Office", "Central Library", "Exam Section", "Conference Boardroom", "Student Affairs Desk"]
    },
    {
        "id": "main_gate", "name": "Main Gate", "type": "Entrance",
        "description": "The primary campus gateway on Babupeth, Ballarpur Road, featuring security gatehouse, campus directory map, and pedestrian plaza.",
        "facilities": ["Security Gatehouse", "Visitor Registration Desk", "Directional Signage", "Main Campus Plaza"]
    },
]

def _response(payload: dict[str, Any], status: int = 200):
    return jsonify(payload), status


def _sync_weather_alerts(forecast: dict[str, Any], air: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    insights = weather_insights(forecast, air)
    for insight in insights:
        key = "|".join((str(insight.get("category")), str(insight.get("title")), str(insight.get("time_window"))))
        database.upsert_alert(
            category=str(insight.get("category", "weather")), severity=str(insight.get("severity", "warning")),
            title=str(insight.get("title", "Weather advisory")), message=str(insight.get("message", "")),
            source=str(insight.get("source", "Open-Meteo")),
            support={"value": insight.get("value"), "unit": insight.get("unit"),
                     "time_window": insight.get("time_window"), "classification": insight.get("classification", "forecast")},
            dedupe_key=key,
        )
    return insights


@app.get("/")
def home():
    return render_template("index.html")


@app.get("/api/health")
def health():
    try:
        db_ok = database.database_health()
    except sqlite3.Error:
        db_ok = False
    model_path = Path(__file__).resolve().parent / "models" / "yolo11n.onnx"
    return _response({"success": db_ok, "status": "ok" if db_ok else "degraded",
                      "service": "RCERT Smart Campus Digital Twin", "timestamp": database.utc_now(),
                      "database": {"available": db_ok, "path": str(DATABASE_PATH)},
                      "weather": {"provider": "Open-Meteo", "key_required": False},
                      "vision": {"model_file_present": model_path.is_file(), "model": "YOLO11n ONNX",
                                 "camera": "opt-in browser capture"}}, 200 if db_ok else 503)


@app.get("/api/weather/current")
def weather_current():
    payload = weather_service.current()
    return _response(payload, 200 if payload.get("success") else 503)


@app.get("/api/weather/forecast")
def weather_forecast():
    payload = weather_service.forecast()
    if payload.get("success"):
        _sync_weather_alerts(payload)
    return _response(payload, 200 if payload.get("success") else 503)


@app.get("/api/air-quality")
def air_quality():
    payload = weather_service.air_quality()
    if payload.get("success"):
        _sync_weather_alerts(weather_service.forecast(), payload)
    return _response(payload, 200 if payload.get("success") else 503)


@app.get("/api/campus")
def campus():
    return _response({"success": True, "source": CAMPUS["source"], "classification": CAMPUS["classification"],
                      "retrieved_at": CAMPUS["retrieved_at"], "campus": CAMPUS})


@app.get("/api/campus/zones")
@app.get("/api/campus-zones")
def campus_zones():
    return _response({"success": True, "source": "RCERT project campus zone list", "classification": "institutional_info",
                      "geometry_classification": "conceptual", "zones": CAMPUS_ZONES})


@app.get("/api/analytics/summary")
def analytics_summary():
    movement = vision_service.summary()
    current, air = weather_service.current(), weather_service.air_quality()
    return _response({"success": True, "classification": "mixed_sources", "timestamp": database.utc_now(),
                      "source": ["Open-Meteo forecast", "validated anonymous camera events"],
                      "weather": current.get("data", {}).get("current") if current.get("success") else None,
                      "air_quality": air.get("data", {}).get("current") if air.get("success") else None,
                      "weather_available": bool(current.get("success")), "air_quality_available": bool(air.get("success")),
                      "movement": movement, "camera_count": len(database.list_cameras()),
                      "active_alerts": len(database.list_alerts(state="active"))})


@app.get("/api/analytics/footfall")
def analytics_footfall():
    try:
        payload = footfall(period=request.args.get("period", "today"), since=request.args.get("since"),
                           until=request.args.get("until"), camera_id=request.args.get("camera_id"))
    except ValueError as exc:
        return _response({"success": False, "error": str(exc)}, 400)
    return _response(payload)


@app.get("/api/analytics/weather")
def analytics_weather():
    forecast, air = weather_service.forecast(), weather_service.air_quality()
    if not forecast.get("success"):
        return _response({"success": False, "source": forecast.get("source"), "classification": "unavailable",
                          "error": forecast.get("error"), "data": None, "insights": []}, 503)
    insights = _sync_weather_alerts(forecast, air if air.get("success") else None)
    return _response({"success": True, "source": forecast.get("source"), "classification": "forecast",
                      "fetched_at": forecast.get("fetched_at"), "stale": forecast.get("stale", False),
                      "data": {"daily": forecast.get("data", {}).get("daily", []),
                               "hourly": forecast.get("data", {}).get("hourly", [])},
                      "air_quality": air.get("data") if air.get("success") else None, "insights": insights})


@app.get("/api/analytics/export.csv")
def analytics_export_csv():
    try:
        stats = footfall(period=request.args.get("period", "7d"), since=request.args.get("since"),
                         until=request.args.get("until"), camera_id=request.args.get("camera_id"))
        events = vision_service.events(camera_id=request.args.get("camera_id"),
                                       since=stats["range"]["since"], until=stats["range"]["until"], limit=1000)
    except ValueError as exc:
        return _response({"success": False, "error": str(exc)}, 400)
    file = io.StringIO()
    fields = ["occurred_at", "camera_id", "zone_id", "direction", "classification"]
    writer = csv.DictWriter(file, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(events)
    return Response(file.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=rcert-footfall.csv"})


@app.get("/api/alerts")
def alerts():
    category, severity, state, query = (request.args.get("category"), request.args.get("severity"),
                                         request.args.get("state", "active"), request.args.get("q"))
    if severity and severity not in {"info", "warning", "critical"}:
        return _response({"success": False, "error": "severity must be info, warning, or critical"}, 400)
    if state not in {"all", "unread", "active", "resolved", "acknowledged"}:
        return _response({"success": False, "error": "invalid alert state filter"}, 400)
    items = database.list_alerts(category=category, severity=severity, state=None if state == "all" else state, query=query)
    return _response({"success": True, "source": "persistent weather/camera/system events", "classification": "event_based",
                      "timestamp": database.utc_now(), "alerts": items, "count": len(items)})


@app.post("/api/alerts/<int:alert_id>/acknowledge")
def acknowledge_alert(alert_id: int):
    item = database.change_alert_state(alert_id, "acknowledge")
    if not item:
        return _response({"success": False, "error": "alert not found"}, 404)
    return _response({"success": True, "alert": item})


@app.post("/api/alerts/<int:alert_id>/resolve")
def resolve_alert(alert_id: int):
    item = database.change_alert_state(alert_id, "resolve")
    if not item:
        return _response({"success": False, "error": "alert not found"}, 404)
    return _response({"success": True, "alert": item})


@app.get("/api/settings")
def get_settings():
    settings = database.get_all_settings()
    return _response({
        "success": True,
        "settings": settings,
        "classification": "user_preferences",
        "timestamp": database.utc_now(),
    })


@app.post("/api/settings")
def update_settings():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _response({"success": False, "error": "JSON object required"}, 400)
    allowed_keys = {
        "temperature_unit", "wind_unit", "refresh_interval_sec",
        "theme", "presentation_mode", "render_quality"
    }
    for key, value in payload.items():
        if key in allowed_keys:
            database.set_setting(key, value)
    updated = database.get_all_settings()
    return _response({"success": True, "settings": updated})


@app.get("/api/analytics/historical")
def analytics_historical():
    snapshots = database.list_weather_snapshots(kind="weather", limit=30)
    history = []
    for s in snapshots:
        p = s.get("payload", {})
        c = p.get("data", {}).get("current", {})
        if c:
            history.append({
                "fetched_at": s.get("fetched_at"),
                "time": c.get("time"),
                "temperature_c": c.get("temperature_c"),
                "humidity_pct": c.get("humidity_pct"),
                "wind_speed_kmh": c.get("wind_speed_kmh"),
                "pressure_hpa": c.get("pressure_hpa"),
                "condition": c.get("condition"),
            })
    return _response({
        "success": True,
        "classification": "historical_stored_data",
        "source": "SQLite weather_snapshots (Open-Meteo)",
        "count": len(history),
        "history": history,
    })


@app.get("/api/reports/summary")
def reports_summary():
    current = weather_service.current()
    forecast = weather_service.forecast()
    air = weather_service.air_quality()
    alerts_list = database.list_alerts(limit=50)
    insights = _sync_weather_alerts(forecast, air if air.get("success") else None)
    return _response({
        "success": True,
        "classification": "derived_report",
        "timestamp": database.utc_now(),
        "campus": CAMPUS,
        "weather_current": current.get("data", {}).get("current") if current.get("success") else None,
        "daily_forecast": forecast.get("data", {}).get("daily", []) if forecast.get("success") else [],
        "air_quality_current": air.get("data", {}).get("current") if air.get("success") else None,
        "insights": insights,
        "active_alerts_count": len([a for a in alerts_list if not a.get("resolved_at")]),
        "total_alerts_count": len(alerts_list),
        "total_zones": len(CAMPUS_ZONES),
        "attribution": "Weather and air-quality data from Open-Meteo. Institutional facts from RCERT.",
    })


@app.get("/api/reports/weather.csv")
def export_weather_csv():
    forecast = weather_service.forecast()
    hourly = forecast.get("data", {}).get("hourly", []) if forecast.get("success") else []
    file = io.StringIO()
    fields = [
        "time", "temperature_2m", "apparent_temperature", "relative_humidity_2m",
        "precipitation", "precipitation_probability", "wind_speed_10m",
        "wind_gusts_10m", "uv_index", "condition"
    ]
    writer = csv.DictWriter(file, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for row in hourly:
        writer.writerow(row)
    return Response(
        file.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=rcert-weather-forecast.csv"}
    )


@app.get("/api/reports/air-quality.csv")
def export_air_quality_csv():
    air = weather_service.air_quality()
    hourly = air.get("data", {}).get("hourly", []) if air.get("success") else []
    file = io.StringIO()
    fields = [
        "time", "pm2_5", "pm10", "us_aqi", "european_aqi",
        "ozone", "nitrogen_dioxide", "sulphur_dioxide", "carbon_monoxide", "dust"
    ]
    writer = csv.DictWriter(file, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for row in hourly:
        writer.writerow(row)
    return Response(
        file.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=rcert-air-quality.csv"}
    )


@app.get("/api/reports/alerts.csv")
def export_alerts_csv():
    alerts_list = database.list_alerts(limit=500)
    file = io.StringIO()
    fields = [
        "id", "created_at", "category", "severity", "title",
        "message", "source", "acknowledged_at", "resolved_at"
    ]
    writer = csv.DictWriter(file, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for a in alerts_list:
        writer.writerow(a)
    return Response(
        file.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=rcert-campus-alerts.csv"}
    )


@app.get("/api/cameras")
@app.get("/api/cameras/status")
def cameras_status():
    items = database.list_cameras()
    now = datetime.now(timezone.utc)
    connected_count = 0
    for item in items:
        age_seconds = None
        try:
            stamp = datetime.fromisoformat(item["updated_at"].replace("Z", "+00:00"))
            age_seconds = max(0.0, (now - stamp.astimezone(timezone.utc)).total_seconds())
        except (KeyError, TypeError, ValueError):
            pass
        item["status_age_seconds"] = age_seconds
        item["stale"] = item.get("status") == "connected" and (age_seconds is None or age_seconds > 30)
        if item["stale"]:
            item["reported_status"] = item["status"]
            item["status"] = "stale"
        if item.get("status") == "connected":
            connected_count += 1
    return _response({"success": True, "source": "browser-reported camera state", "classification": "operational_status",
                      "timestamp": database.utc_now(), "cameras": items, "connected_count": connected_count})


@app.post("/api/cameras/connect")
def camera_connect():
    try:
        camera = vision_service.update_camera(request.get_json(silent=True), status="connected")
    except vision_service.EventValidationError as exc:
        return _response({"success": False, "error": str(exc)}, 400)
    return _response({"success": True, "camera": camera}, 201)


@app.post("/api/cameras/stop")
def camera_stop():
    try:
        camera = vision_service.update_camera(request.get_json(silent=True), status="stopped")
    except vision_service.EventValidationError as exc:
        return _response({"success": False, "error": str(exc)}, 400)
    return _response({"success": True, "camera": camera})


@app.post("/api/vision/config")
def vision_config():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _response({"success": False, "error": "a JSON object is required"}, 400)
    camera_id, zone_id = payload.get("camera_id"), payload.get("zone_id")
    if not isinstance(camera_id, str) or not camera_id or len(camera_id) > 64:
        return _response({"success": False, "error": "camera_id is required"}, 400)
    if zone_id is not None and zone_id not in vision_service.ZONE_IDS:
        return _response({"success": False, "error": "unknown zone_id"}, 400)
    try:
        confidence = float(payload.get("confidence", 0.55))
    except (TypeError, ValueError):
        return _response({"success": False, "error": "confidence must be numeric"}, 400)
    if not math.isfinite(confidence) or not 0.2 <= confidence <= 0.95:
        return _response({"success": False, "error": "confidence must be between 0.20 and 0.95"}, 400)
    line = payload.get("line")
    if not isinstance(line, dict) or not isinstance(line.get("start"), list) or not isinstance(line.get("end"), list) or len(line["start"]) != 2 or len(line["end"]) != 2:
        return _response({"success": False, "error": "line must contain start and end normalized coordinate pairs"}, 400)
    try:
        coords = [float(value) for point in (line["start"], line["end"]) for value in point]
    except (TypeError, ValueError):
        return _response({"success": False, "error": "line coordinates must be numbers"}, 400)
    if not all(math.isfinite(value) and 0 <= value <= 1 for value in coords) or coords[:2] == coords[2:]:
        return _response({"success": False, "error": "line coordinates must be distinct normalized values between 0 and 1"}, 400)
    direction = payload.get("entry_direction", "left_to_right")
    if direction not in {"left_to_right", "right_to_left", "top_to_bottom", "bottom_to_top"}:
        return _response({"success": False, "error": "invalid entry_direction"}, 400)
    config = database.save_camera_config(camera_id=camera_id, zone_id=zone_id, line=line,
                                         entry_direction=direction, confidence=confidence)
    return _response({"success": True, "classification": "camera_session_config", "camera_id": camera_id,
                      "zone_id": zone_id, "confidence": confidence, "line": line,
                      "entry_direction": direction, "updated_at": config["updated_at"],
                      "source": "persisted local camera configuration"})


@app.get("/api/vision/config/<camera_id>")
def get_vision_config(camera_id: str):
    try:
        config = database.get_camera_config(camera_id)
    except sqlite3.Error as exc:
        return _response({"success": False, "error": f"configuration read failed: {exc}"}, 500)
    if not config:
        return _response({"success": False, "error": "camera configuration not found"}, 404)
    return _response({"success": True, "classification": "camera_session_config", "config": config})


@app.get("/api/vision/events")
def vision_events():
    try:
        items = vision_service.events(camera_id=request.args.get("camera_id"), zone_id=request.args.get("zone_id"),
                                      since=request.args.get("since"), until=request.args.get("until"),
                                      limit=int(request.args.get("limit", "200")))
    except (ValueError, TypeError) as exc:
        return _response({"success": False, "error": str(exc)}, 400)
    return _response({"success": True, "source": "validated anonymous camera events",
                      "classification": "actual_camera", "timestamp": database.utc_now(),
                      "events": items, "count": len(items)})


@app.post("/api/vision/events")
def ingest_vision_event():
    try:
        item, duplicate = vision_service.ingest_event(request.get_json(silent=True))
    except vision_service.EventValidationError as exc:
        return _response({"success": False, "error": str(exc)}, 400)
    except sqlite3.IntegrityError:
        return _response({"success": False, "error": "event id was already submitted"}, 409)
    return _response({"success": True, "event": item, "duplicate": duplicate,
                      "classification": "actual_camera", "source": "browser YOLO11n inference"}, 200 if duplicate else 201)


@app.get("/api/vision/summary")
def vision_summary():
    return _response({"success": True, **vision_service.summary()})


@app.post("/api/vision/infer")
def vision_infer():
    if request.mimetype != "image/jpeg":
        return _response({"success": False, "error": "send a JPEG frame using Content-Type: image/jpeg"}, 415)
    image_bytes = request.get_data(cache=False)
    if not image_bytes or len(image_bytes) > 3_500_000:
        return _response({"success": False, "error": "JPEG frame must be between 1 byte and 3.5 MB"}, 413)
    try:
        confidence = float(request.headers.get("X-Confidence-Threshold", request.args.get("confidence", "0.55")))
    except (TypeError, ValueError):
        return _response({"success": False, "error": "confidence must be numeric"}, 400)
    if not math.isfinite(confidence) or not 0.2 <= confidence <= 0.95:
        return _response({"success": False, "error": "confidence must be between 0.20 and 0.95"}, 400)
    try:
        from vision_pipeline import infer_people
        result = infer_people(image_bytes, confidence_threshold=confidence)
    except (ImportError, FileNotFoundError, RuntimeError, ValueError) as exc:
        return _response({"success": False, "error": f"YOLO11n inference unavailable: {exc}",
                          "source": "YOLO11n ONNX", "classification": "unavailable"}, 503)
    return _response({"success": True, "source": "YOLO11n ONNX", "classification": "actual_camera",
                      "timestamp": database.utc_now(), "detections": result.get("detections", []),
                      "latency_ms": result.get("latency_ms"), "inference_fps": result.get("inference_fps")})


@app.get("/api/vision/events.csv")
def vision_events_csv():
    try:
        items = vision_service.events(camera_id=request.args.get("camera_id"), zone_id=request.args.get("zone_id"),
                                      since=request.args.get("since"), until=request.args.get("until"), limit=1000)
    except ValueError as exc:
        return _response({"success": False, "error": str(exc)}, 400)
    file = io.StringIO()
    fields = ["occurred_at", "camera_id", "zone_id", "direction", "classification"]
    writer = csv.DictWriter(file, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(items)
    return Response(file.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=rcert-vision-events.csv"})


# Legacy compatibility routes; simulation is disabled and old rows retain source labels.
@app.get("/api/latest-data")
def legacy_latest_data():
    reading = database.latest_iot_reading()
    if not reading:
        return _response({"success": False,
                          "error": "No actual IoT readings are available; synthetic legacy data is excluded.",
                          "data": None, "classification": "unavailable",
                          "predictions": {"occupancy": None, "energy": None}}, 503)
    return _response({"success": True, "data": reading, "source": reading.get("source"),
                      "timestamp": reading.get("timestamp"), "classification": "actual_iot",
                      "predictions": {"occupancy": None, "energy": None}})


@app.post("/api/simulate-reading")
def legacy_simulate_reading_disabled():
    return _response({"success": False, "error": "Synthetic sensor generation is disabled. Use an explicitly isolated demo mode.",
                      "classification": "disabled"}, 410)


@app.post("/api/iot-data")
def receive_iot_data():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return _response({"success": False, "error": "JSON object required"}, 400)
    ranges = {"temperature": (-50, 60), "humidity": (0, 100), "electricity": (0, 1_000_000),
              "water": (0, 1_000_000), "occupancy": (0, 100)}
    unknown = set(data) - set(ranges)
    if unknown:
        return _response({"success": False, "error": f"unsupported field: {sorted(unknown)[0]}"}, 400)
    if not data:
        return _response({"success": False, "error": "at least one measured sensor field is required"}, 400)
    values: dict[str, float] = {}
    for key, raw in data.items():
        bounds = ranges[key]
        try:
            value = float(raw)
        except (TypeError, ValueError):
            return _response({"success": False, "error": f"{key} must be numeric"}, 400)
        if not math.isfinite(value) or not bounds[0] <= value <= bounds[1]:
            return _response({"success": False, "error": f"{key} is outside the accepted range"}, 400)
        values[key] = value
    try:
        reading = database.insert_iot_reading(values)
    except sqlite3.Error as exc:
        return _response({"success": False, "error": f"database write failed: {exc}"}, 500)
    return _response({"success": True, "message": "IoT data stored", "data": reading,
                      "source": "ESP32_IoT", "timestamp": reading["timestamp"],
                      "classification": "actual_iot"}, 201)


@app.get("/api/history")
def legacy_history():
    legacy = database.legacy_sensor_readings(limit=100)
    return _response({"success": True, "timestamp": database.utc_now(),
                      "classification": "separated_sources", "source": "actual IoT measurements and isolated legacy rows",
                      "actual_iot": database.list_iot_readings(limit=100),
                      "legacy_sensor_rows": legacy})


@app.get("/api/analytics")
def legacy_analytics():
    return _response({"success": True, "data": vision_service.summary(),
                      "source": "validated anonymous camera events", "classification": "actual_camera",
                      "message": "Legacy alias; synthetic sensor data is excluded."})


@app.get("/api/system-summary")
def legacy_system_summary():
    summary = vision_service.summary()
    return _response({"success": True, "total_zones": len(CAMPUS_ZONES), "camera_events": summary["total_events"],
                      "connected_cameras": sum(1 for item in database.list_cameras() if item.get("status") == "connected"),
                      "source": summary["source"], "classification": summary["classification"], "timestamp": database.utc_now()})


@app.errorhandler(413)
def too_large(_error):
    return _response({"success": False, "error": "request body exceeds the 4 MB application limit"}, 413)


@app.errorhandler(404)
def not_found(_error):
    if request.path.startswith("/api/"):
        return _response({"success": False, "error": "API route not found"}, 404)
    return "Not found", 404


if __name__ == "__main__":
    print("RCERT Smart Campus Digital Twin")
    print("Dashboard: http://127.0.0.1:5001")
    print("Weather: Open-Meteo forecast API; camera access is opt-in")
    app.run(host="127.0.0.1", port=5001, debug=False, use_reloader=False)
