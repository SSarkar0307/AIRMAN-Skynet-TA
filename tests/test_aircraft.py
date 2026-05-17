from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.db.models import AircraftStatus, DefectSeverity, SortieStatus
from tests.conftest import create_sortie_direct


def future_payload(sortie_number: str, aircraft_id: int, base_id: int = 1):
    start = datetime.now(timezone.utc) + timedelta(days=11)
    end = start + timedelta(hours=1)
    return {
        "sortie_number": sortie_number,
        "cadet_id": 5,
        "instructor_id": 3,
        "aircraft_id": aircraft_id,
        "base_id": base_id,
        "lesson_type": "Circuit Pattern",
        "scheduled_start": start.isoformat(),
        "scheduled_end": end.isoformat(),
    }


def test_grounded_aircraft_cannot_be_assigned_to_new_sortie(client, dispatcher_headers):
    response = client.post("/sorties", json=future_payload("A900", aircraft_id=2), headers=dispatcher_headers)
    assert response.status_code == 409
    assert response.json()["error"] == "CONFLICT"


def test_grounded_aircraft_cannot_be_released(client, dispatcher_headers, app):
    sortie = create_sortie_direct(app, sortie_number="GROUND-1", cadet_id=5, instructor_id=3, aircraft_id=2, base_id=1)
    response = client.patch(f"/sorties/{sortie.id}/release", headers=dispatcher_headers)
    assert response.status_code == 409
    assert response.json()["error"] in {"CONFLICT", "INVALID_STATE_TRANSITION"}


def test_aircraft_becomes_airborne_and_landed(client, dispatcher_headers):
    assert client.patch("/sorties/1/release", headers=dispatcher_headers).status_code == 200
    assert client.patch("/sorties/1/airborne", headers=dispatcher_headers).status_code == 200
    aircraft = client.get("/aircraft/1", headers=dispatcher_headers).json()
    assert aircraft["status"] == AircraftStatus.AIRBORNE.value

    assert client.patch("/sorties/1/landed", headers=dispatcher_headers).status_code == 200
    aircraft = client.get("/aircraft/1", headers=dispatcher_headers).json()
    assert aircraft["status"] == AircraftStatus.LANDED.value


def test_critical_defect_grounds_aircraft(client, maint_headers):
    response = client.post(
        "/defects",
        headers=maint_headers,
        json={
            "aircraft_id": 1,
            "severity": DefectSeverity.CRITICAL.value,
            "description": "Engine issue",
        },
    )
    assert response.status_code == 200
    aircraft = client.get("/aircraft/1", headers=maint_headers).json()
    assert aircraft["status"] == AircraftStatus.GROUNDED.value


def test_aircraft_cannot_become_ready_until_defect_resolved_or_deferred(client, maint_headers):
    response = client.post(
        "/defects",
        headers=maint_headers,
        json={
            "aircraft_id": 1,
            "severity": DefectSeverity.CRITICAL.value,
            "description": "Hydraulic issue",
        },
    )
    assert response.status_code == 200
    ready = client.patch("/aircraft/1/ready", headers=maint_headers)
    assert ready.status_code == 409
    assert ready.json()["error"] == "CONFLICT"

