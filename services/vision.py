"""Validation and persistence boundary for anonymous camera events."""
from __future__ import annotations

import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import database

ZONE_IDS = {
    "boys_hostel", "mba", "polytechnic", "mining", "computer_science", "civil",
    "data_science", "mechanical", "electrical", "electrical_workshop", "auditorium",
    "canteen", "gym", "girls_hostel", "boys_parking", "girls_parking",
    "main_building", "main_gate",
}
TOKEN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
ALLOWED_EVENT_FIELDS = {
    "event_id", "camera_id", "zone_id", "session_id", "track_id",
    "event_type", "direction", "occurred_at",
}


class EventValidationError(ValueError):
    pass


def _token(value: Any, field: str) -> str:
    if not isinstance(value, str) or not TOKEN.fullmatch(value):
        raise EventValidationError(f"{field} must be 1-64 letters, digits, '_' or '-'")
    return value


def _timestamp(value: Any) -> str:
    if not isinstance(value, str) or len(value) > 40:
        raise EventValidationError("occurred_at must be an ISO-8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise EventValidationError("occurred_at must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise EventValidationError("occurred_at must include a timezone")
    now = datetime.now(timezone.utc)
    instant = parsed.astimezone(timezone.utc)
    if instant > now + timedelta(minutes=5) or instant < now - timedelta(days=30):
        raise EventValidationError("occurred_at is outside the accepted time window")
    return instant.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def validate_event(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise EventValidationError("a JSON object is required")
    unknown = set(payload) - ALLOWED_EVENT_FIELDS
    if unknown:
        raise EventValidationError(f"unsupported field: {sorted(unknown)[0]}")
    camera_id = _token(payload.get("camera_id"), "camera_id")
    session_id = _token(payload.get("session_id"), "session_id")
    track_id = _token(payload.get("track_id"), "track_id")
    event_type = payload.get("event_type")
    direction = payload.get("direction")
    if event_type not in {"entry", "exit"}:
        raise EventValidationError("event_type must be entry or exit")
    if direction not in {"entry", "exit"} or direction != event_type:
        raise EventValidationError("direction must match event_type and be entry or exit")
    zone_id = payload.get("zone_id")
    if zone_id is not None and zone_id not in ZONE_IDS:
        raise EventValidationError("zone_id is not a known campus zone")
    occurred_at = _timestamp(payload.get("occurred_at"))
    event_id = payload.get("event_id")
    if event_id is None:
        event_id = uuid.uuid4().hex
    else:
        event_id = _token(event_id, "event_id")
    return {
        "event_id": event_id,
        "camera_id": camera_id,
        "zone_id": zone_id,
        "session_id": session_id,
        "track_id": track_id,
        "event_type": event_type,
        "direction": direction,
        "occurred_at": occurred_at,
        "ingested_at": database.utc_now(),
        "classification": "actual_camera",
    }


def ingest_event(payload: Any) -> tuple[dict[str, Any], bool]:
    event = validate_event(payload)
    stored = database.insert_vision_event(event)
    return stored, bool(stored.get("duplicate"))


def events(*, camera_id: str | None = None, zone_id: str | None = None,
           since: str | None = None, until: str | None = None, limit: int = 200) -> list[dict[str, Any]]:
    if camera_id is not None:
        camera_id = _token(camera_id, "camera_id")
    if zone_id is not None and zone_id not in ZONE_IDS:
        raise EventValidationError("zone_id is not a known campus zone")
    return database.list_vision_events(camera_id=camera_id, zone_id=zone_id, since=since, until=until, limit=limit)


def summary(*, since: str | None = None, until: str | None = None) -> dict[str, Any]:
    result = database.summarize_vision_events(since=since, until=until)
    result["fetched_at"] = database.utc_now()
    result["has_data"] = result["total_events"] > 0
    return result


def update_camera(payload: Any, *, status: str) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise EventValidationError("a JSON object is required")
    camera_id = _token(payload.get("camera_id"), "camera_id")
    session_id = payload.get("session_id")
    if session_id is not None:
        session_id = _token(session_id, "session_id")
    zone_id = payload.get("zone_id")
    if zone_id is not None and zone_id not in ZONE_IDS:
        raise EventValidationError("zone_id is not a known campus zone")
    name = payload.get("display_name") or "Browser camera"
    if not isinstance(name, str) or not name.strip() or len(name) > 80:
        raise EventValidationError("display_name must be 1-80 characters")
    error = payload.get("error")
    if error is not None and (not isinstance(error, str) or len(error) > 200):
        raise EventValidationError("error must be at most 200 characters")
    return database.upsert_camera(camera_id=camera_id, display_name=name.strip(), zone_id=zone_id,
                                  status=status, session_id=session_id, last_error=error)
