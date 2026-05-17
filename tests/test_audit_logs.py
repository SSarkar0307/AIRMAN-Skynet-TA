from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.db.models import DefectSeverity


def future_payload(sortie_number: str):
    start = datetime.now(timezone.utc) + timedelta(days=15)
    end = start + timedelta(hours=1)
    return {
        "sortie_number": sortie_number,
        "cadet_id": 5,
        "instructor_id": 3,
        "aircraft_id": 1,
        "base_id": 1,
        "lesson_type": "Audit Run",
        "scheduled_start": start.isoformat(),
        "scheduled_end": end.isoformat(),
    }


def test_audit_log_created_for_sortie_release(client, dispatcher_headers, admin_headers):
    sortie = client.post("/sorties", json=future_payload("AL-1"), headers=dispatcher_headers).json()
    assert client.patch(f"/sorties/{sortie['id']}/release", headers=dispatcher_headers).status_code == 200
    response = client.get(f"/audit-logs?entity_type=sortie&entity_id={sortie['id']}", headers=admin_headers)
    assert response.status_code == 200
    logs = response.json()
    assert any(log["action"] == "SORTIE_RELEASED" for log in logs)


def test_audit_log_created_for_defect_creation(client, maint_headers, admin_headers):
    response = client.post(
        "/defects",
        headers=maint_headers,
        json={"aircraft_id": 1, "severity": DefectSeverity.LOW.value, "description": "Light issue"},
    )
    assert response.status_code == 200
    defect_id = response.json()["id"]
    logs = client.get(f"/audit-logs?entity_type=defect&entity_id={defect_id}", headers=admin_headers).json()
    assert any(log["action"] == "DEFECT_CREATED" for log in logs)


def test_audit_log_created_for_training_approval(client, dispatcher_headers, instructor_headers, cfi_headers, admin_headers):
    sortie = client.post("/sorties", json=future_payload("AL-2"), headers=dispatcher_headers).json()
    progress = client.post(
        "/training-progress",
        headers=instructor_headers,
        json={"sortie_id": sortie["id"], "maneuver_score": 4, "communication_score": 4, "situational_awareness_score": 4, "remarks": "draft"},
    ).json()
    assert client.patch(
        f"/training-progress/{progress['id']}/submit",
        headers=instructor_headers,
        json={"maneuver_score": 4, "communication_score": 4, "situational_awareness_score": 4, "remarks": "ready"},
    ).status_code == 200
    assert client.patch(f"/training-progress/{progress['id']}/approve", headers=cfi_headers).status_code == 200
    logs = client.get(f"/audit-logs?entity_type=training_progress&entity_id={progress['id']}", headers=admin_headers).json()
    assert any(log["action"] == "TRAINING_APPROVED" for log in logs)


def test_audit_log_contains_expected_fields(client, dispatcher_headers, admin_headers):
    sortie = client.post("/sorties", json=future_payload("AL-3"), headers=dispatcher_headers).json()
    client.patch(f"/sorties/{sortie['id']}/release", headers=dispatcher_headers)
    logs = client.get(f"/audit-logs?entity_type=sortie&entity_id={sortie['id']}", headers=admin_headers).json()
    log = next(item for item in logs if item["action"] == "SORTIE_RELEASED")
    assert log["actor_id"]
    assert log["actor_role"]
    assert log["entity_type"] == "sortie"
    assert log["old_value"] is not None
    assert log["new_value"] is not None

