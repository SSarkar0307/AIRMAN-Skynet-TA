from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.db.models import RoleEnum
from tests.conftest import auth_headers, create_user


def future_payload(sortie_number: str):
    start = datetime.now(timezone.utc) + timedelta(days=12)
    end = start + timedelta(hours=1)
    return {
        "sortie_number": sortie_number,
        "cadet_id": 5,
        "instructor_id": 3,
        "aircraft_id": 1,
        "base_id": 1,
        "lesson_type": "Navigation",
        "scheduled_start": start.isoformat(),
        "scheduled_end": end.isoformat(),
    }


def create_progress_for_test(client, dispatcher_headers, instructor_headers):
    sortie = client.post("/sorties", json=future_payload("TP-1"), headers=dispatcher_headers).json()
    sortie_id = sortie["id"]
    progress = client.post(
        "/training-progress",
        headers=instructor_headers,
        json={"sortie_id": sortie_id, "maneuver_score": 3, "communication_score": 3, "situational_awareness_score": 3, "remarks": "draft"},
    )
    assert progress.status_code == 200
    return sortie_id, progress.json()["id"]


def test_assigned_instructor_can_submit_training_progress(client, dispatcher_headers, instructor_headers):
    sortie_id, progress_id = create_progress_for_test(client, dispatcher_headers, instructor_headers)
    response = client.patch(
        f"/training-progress/{progress_id}/submit",
        headers=instructor_headers,
        json={"maneuver_score": 4, "communication_score": 4, "situational_awareness_score": 4, "remarks": "Good sortie"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "SUBMITTED"


def test_non_assigned_instructor_cannot_submit_training_progress(client, dispatcher_headers, app):
    create_user(app, email="backup.instructor@airman.test", role=RoleEnum.INSTRUCTOR, base_id=1, full_name="Backup Instructor")
    seed_instructor_headers = auth_headers(client, "rao@airman.test", "INSTRUCTOR")
    _, progress_id = create_progress_for_test(client, dispatcher_headers, seed_instructor_headers)
    other_headers = auth_headers(client, "backup.instructor@airman.test", "INSTRUCTOR")
    response = client.patch(
        f"/training-progress/{progress_id}/submit",
        headers=other_headers,
        json={"maneuver_score": 4, "communication_score": 4, "situational_awareness_score": 4, "remarks": "Attempt"},
    )
    assert response.status_code == 403


def test_cadet_cannot_submit_training_progress(client, dispatcher_headers, instructor_headers, cadet_headers):
    _, progress_id = create_progress_for_test(client, dispatcher_headers, instructor_headers)
    response = client.patch(
        f"/training-progress/{progress_id}/submit",
        headers=cadet_headers,
        json={"maneuver_score": 4, "communication_score": 4, "situational_awareness_score": 4, "remarks": "Nope"},
    )
    assert response.status_code == 403


def test_cfi_can_approve_training_progress(client, dispatcher_headers, instructor_headers, cfi_headers):
    _, progress_id = create_progress_for_test(client, dispatcher_headers, instructor_headers)
    assert client.patch(
        f"/training-progress/{progress_id}/submit",
        headers=instructor_headers,
        json={"maneuver_score": 4, "communication_score": 4, "situational_awareness_score": 4, "remarks": "Fine"},
    ).status_code == 200
    response = client.patch(f"/training-progress/{progress_id}/approve", headers=cfi_headers)
    assert response.status_code == 200
    assert response.json()["status"] == "APPROVED"


def test_dispatcher_cannot_approve_training_progress(client, dispatcher_headers, instructor_headers):
    _, progress_id = create_progress_for_test(client, dispatcher_headers, instructor_headers)
    assert client.patch(
        f"/training-progress/{progress_id}/submit",
        headers=instructor_headers,
        json={"maneuver_score": 4, "communication_score": 4, "situational_awareness_score": 4, "remarks": "Fine"},
    ).status_code == 200
    response = client.patch(f"/training-progress/{progress_id}/approve", headers=dispatcher_headers)
    assert response.status_code == 403


def test_score_below_one_rejected(client, dispatcher_headers, instructor_headers):
    _, progress_id = create_progress_for_test(client, dispatcher_headers, instructor_headers)
    response = client.patch(
        f"/training-progress/{progress_id}/submit",
        headers=instructor_headers,
        json={"maneuver_score": 0, "communication_score": 4, "situational_awareness_score": 4, "remarks": "Bad"},
    )
    assert response.status_code == 422
    assert response.json()["error"] == "VALIDATION_ERROR"


def test_score_above_five_rejected(client, dispatcher_headers, instructor_headers):
    _, progress_id = create_progress_for_test(client, dispatcher_headers, instructor_headers)
    response = client.patch(
        f"/training-progress/{progress_id}/submit",
        headers=instructor_headers,
        json={"maneuver_score": 6, "communication_score": 4, "situational_awareness_score": 4, "remarks": "Bad"},
    )
    assert response.status_code == 422


def test_empty_remarks_rejected_during_submission(client, dispatcher_headers, instructor_headers):
    _, progress_id = create_progress_for_test(client, dispatcher_headers, instructor_headers)
    response = client.patch(
        f"/training-progress/{progress_id}/submit",
        headers=instructor_headers,
        json={"maneuver_score": 4, "communication_score": 4, "situational_awareness_score": 4, "remarks": "   "},
    )
    assert response.status_code == 422
