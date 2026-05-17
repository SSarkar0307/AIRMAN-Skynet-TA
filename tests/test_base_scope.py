from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.db.models import RoleEnum
from tests.conftest import create_sortie_direct, create_user


def future_payload(sortie_number: str, aircraft_id: int = 1, base_id: int = 1):
    start = datetime.now(timezone.utc) + timedelta(days=14)
    end = start + timedelta(hours=1)
    return {
        "sortie_number": sortie_number,
        "cadet_id": 5,
        "instructor_id": 3,
        "aircraft_id": aircraft_id,
        "base_id": base_id,
        "lesson_type": "Cross Country",
        "scheduled_start": start.isoformat(),
        "scheduled_end": end.isoformat(),
    }


def test_base_a_dispatcher_cannot_access_base_b_sortie(client, dispatcher_headers, app):
    mumbai_cadet = create_user(app, email="mum.cadet@airman.test", role=RoleEnum.CADET, base_id=2, full_name="Mumbai Cadet")
    mumbai_instructor = create_user(app, email="mum.instructor@airman.test", role=RoleEnum.INSTRUCTOR, base_id=2, full_name="Mumbai Instructor")
    sortie = create_sortie_direct(app, sortie_number="MB-1", cadet_id=mumbai_cadet.id, instructor_id=mumbai_instructor.id, aircraft_id=3, base_id=2)
    response = client.get(f"/sorties/{sortie.id}", headers=dispatcher_headers)
    assert response.status_code == 403


def test_base_mismatch_aircraft_assignment_rejected(client, dispatcher_headers):
    response = client.post("/sorties", json=future_payload("B900", aircraft_id=3, base_id=1), headers=dispatcher_headers)
    assert response.status_code == 409
    assert response.json()["error"] == "CONFLICT"


def test_user_cannot_change_base_id_to_access_another_base(client, dispatcher_headers):
    response = client.post("/sorties", json=future_payload("B901", base_id=2), headers=dispatcher_headers)
    assert response.status_code == 403
