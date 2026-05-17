from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.db.models import SortieStatus


def future_window():
    start = datetime.now(timezone.utc) + timedelta(days=10)
    end = start + timedelta(hours=1)
    return start.isoformat(), end.isoformat()


def create_sortie_payload(sortie_number: str, aircraft_id: int = 1, base_id: int = 1):
    start, end = future_window()
    return {
        "sortie_number": sortie_number,
        "cadet_id": 5,
        "instructor_id": 3,
        "aircraft_id": aircraft_id,
        "base_id": base_id,
        "lesson_type": "Circuit Pattern",
        "scheduled_start": start,
        "scheduled_end": end,
    }


def test_dispatcher_can_create_scheduled_sortie(client, dispatcher_headers):
    response = client.post("/sorties", json=create_sortie_payload("S900"), headers=dispatcher_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == SortieStatus.SCHEDULED.value
    assert body["sortie_number"] == "S900"


def test_dispatcher_can_release_mark_airborne_and_land_sortie(client, dispatcher_headers):
    response = client.patch("/sorties/1/release", headers=dispatcher_headers)
    assert response.status_code == 200
    assert response.json()["status"] == SortieStatus.RELEASED.value

    response = client.patch("/sorties/1/airborne", headers=dispatcher_headers)
    assert response.status_code == 200
    assert response.json()["status"] == SortieStatus.AIRBORNE.value

    response = client.patch("/sorties/1/landed", headers=dispatcher_headers)
    assert response.status_code == 200
    assert response.json()["status"] == SortieStatus.LANDED.value


def test_cannot_mark_scheduled_sortie_airborne_directly(client, dispatcher_headers):
    response = client.patch("/sorties/1/airborne", headers=dispatcher_headers)
    assert response.status_code == 409
    assert response.json()["error"] == "INVALID_STATE_TRANSITION"


def test_cannot_close_sortie_before_training_approval(client, dispatcher_headers):
    response = client.patch("/sorties/5/close", headers=dispatcher_headers)
    assert response.status_code == 409
    assert response.json()["error"] == "INVALID_STATE_TRANSITION"


def test_closed_sortie_cannot_be_released_again(client, dispatcher_headers, instructor_headers, cfi_headers):
    created = client.post("/sorties", json=create_sortie_payload("S901"), headers=dispatcher_headers).json()
    sortie_id = created["id"]

    assert client.patch(f"/sorties/{sortie_id}/release", headers=dispatcher_headers).status_code == 200
    assert client.patch(f"/sorties/{sortie_id}/airborne", headers=dispatcher_headers).status_code == 200
    assert client.patch(f"/sorties/{sortie_id}/landed", headers=dispatcher_headers).status_code == 200

    progress = client.post(
        "/training-progress",
        headers=instructor_headers,
        json={
            "sortie_id": sortie_id,
            "maneuver_score": 4,
            "communication_score": 4,
            "situational_awareness_score": 4,
            "remarks": "draft",
        },
    ).json()
    submit = client.patch(
        f"/training-progress/{progress['id']}/submit",
        headers=instructor_headers,
        json={
            "maneuver_score": 4,
            "communication_score": 4,
            "situational_awareness_score": 4,
            "remarks": "solid flight",
        },
    )
    assert submit.status_code == 200
    assert client.patch(f"/training-progress/{progress['id']}/approve", headers=cfi_headers).status_code == 200
    assert client.patch(f"/sorties/{sortie_id}/close", headers=dispatcher_headers).status_code == 200

    response = client.patch(f"/sorties/{sortie_id}/release", headers=dispatcher_headers)
    assert response.status_code == 409
    assert response.json()["error"] == "INVALID_STATE_TRANSITION"
