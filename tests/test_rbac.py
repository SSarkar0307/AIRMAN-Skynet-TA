from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.db.models import RoleEnum
from tests.conftest import create_sortie_direct, create_user


def future_payload(sortie_number: str, cadet_id: int = 5, instructor_id: int = 3, aircraft_id: int = 1, base_id: int = 1):
    start = datetime.now(timezone.utc) + timedelta(days=13)
    end = start + timedelta(hours=1)
    return {
        "sortie_number": sortie_number,
        "cadet_id": cadet_id,
        "instructor_id": instructor_id,
        "aircraft_id": aircraft_id,
        "base_id": base_id,
        "lesson_type": "Sim",
        "scheduled_start": start.isoformat(),
        "scheduled_end": end.isoformat(),
    }


def test_cadet_can_view_own_sortie_only(client, cadet_headers):
    response = client.get("/sorties/1", headers=cadet_headers)
    assert response.status_code == 200


def test_cadet_cannot_view_another_cadets_sortie(client, cadet_headers, app):
    other_cadet = create_user(app, email="other.cadet@airman.test", role=RoleEnum.CADET, base_id=1, full_name="Other Cadet")
    sortie = create_sortie_direct(app, sortie_number="RB-1", cadet_id=other_cadet.id, instructor_id=3, aircraft_id=1, base_id=1)
    response = client.get(f"/sorties/{sortie.id}", headers=cadet_headers)
    assert response.status_code == 403


def test_maintenance_officer_cannot_approve_training_progress(client, dispatcher_headers, instructor_headers, maint_headers):
    sortie = client.post("/sorties", json=future_payload("RB-2"), headers=dispatcher_headers).json()
    progress = client.post(
        "/training-progress",
        headers=instructor_headers,
        json={"sortie_id": sortie["id"], "maneuver_score": 4, "communication_score": 4, "situational_awareness_score": 4, "remarks": "draft"},
    ).json()
    assert client.patch(
        f"/training-progress/{progress['id']}/submit",
        headers=instructor_headers,
        json={"maneuver_score": 4, "communication_score": 4, "situational_awareness_score": 4, "remarks": "good"},
    ).status_code == 200
    response = client.patch(f"/training-progress/{progress['id']}/approve", headers=maint_headers)
    assert response.status_code == 403


def test_dispatcher_cannot_resolve_defect(client, dispatcher_headers):
    response = client.patch("/defects/1/resolve", headers=dispatcher_headers, json={"resolution_note": "not allowed"})
    assert response.status_code == 403


def test_admin_can_access_all_records(client, admin_headers):
    response = client.get("/aircraft/3", headers=admin_headers)
    assert response.status_code == 200

