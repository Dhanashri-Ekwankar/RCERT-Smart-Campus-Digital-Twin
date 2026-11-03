from __future__ import annotations

from datetime import datetime, timezone

import database
from services.vision import EventValidationError, ingest_event, validate_event


def base_event():
    return {"camera_id": "camera-1", "zone_id": "main_gate", "session_id": "session-a", "track_id": "track-1",
            "event_type": "entry", "direction": "entry", "occurred_at": datetime.now(timezone.utc).isoformat()}


def test_event_validation_forces_anonymous_camera_fields():
    event = validate_event(base_event())
    assert event["classification"] == "actual_camera"
    assert event["event_id"]
    try:
        validate_event({**base_event(), "student_name": "not allowed"})
    except EventValidationError:
        pass
    else:
        raise AssertionError("unapproved person-identifying fields must be rejected")


def test_events_reject_naive_or_wrong_direction_times():
    for payload in ({**base_event(), "occurred_at": "2026-11-02T10:00:00"},
                    {**base_event(), "direction": "exit"}):
        try:
            validate_event(payload)
        except EventValidationError:
            continue
        raise AssertionError("invalid event should fail validation")


def test_event_ingestion_duplicate_crossing_is_suppressed(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DATABASE_PATH", tmp_path / "vision.db")
    database.initialize_database()
    first, duplicate1 = ingest_event(base_event())
    second_payload = {**base_event(), "event_id": "retry-event"}
    second, duplicate2 = ingest_event(second_payload)
    assert duplicate1 is False
    assert duplicate2 is True
    assert first["event_id"] == second["event_id"]
    assert database.summarize_vision_events()["total_events"] == 1


def test_demo_or_image_payload_cannot_be_ingested(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DATABASE_PATH", tmp_path / "strict.db")
    database.initialize_database()
    for extra in ({"classification": "demo"}, {"image": "base64"}, {"source": "demo"}):
        try:
            validate_event({**base_event(), **extra})
        except EventValidationError:
            continue
        raise AssertionError("demo/image content must not enter actual camera events")
    assert database.summarize_vision_events()["total_events"] == 0
