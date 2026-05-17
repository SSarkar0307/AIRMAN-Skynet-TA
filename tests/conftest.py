from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.models import AviationBase, RoleEnum, Sortie, SortieStatus, User
from app.main import create_app


@pytest.fixture()
def app(tmp_path):
    db_path = tmp_path / "airman-test.db"
    application = create_app(f"sqlite+pysqlite:///{db_path}")
    return application


@pytest.fixture()
def client(app):
    return TestClient(app)


def auth_headers(client: TestClient, email: str, role: str) -> dict[str, str]:
    response = client.post("/auth/login", json={"email": email, "role": role})
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def dispatcher_headers(client):
    return auth_headers(client, "dispatcher@airman.test", "DISPATCHER")


@pytest.fixture()
def instructor_headers(client):
    return auth_headers(client, "rao@airman.test", "INSTRUCTOR")


@pytest.fixture()
def cfi_headers(client):
    return auth_headers(client, "cfi@airman.test", "CFI")


@pytest.fixture()
def cadet_headers(client):
    return auth_headers(client, "arjun@airman.test", "CADET")


@pytest.fixture()
def maint_headers(client):
    return auth_headers(client, "maint@airman.test", "MAINTENANCE_OFFICER")


@pytest.fixture()
def admin_headers(client):
    return auth_headers(client, "admin@airman.test", "ADMIN")


def session_factory(app):
    return app.state.session_factory


def get_user(app, email: str) -> User:
    with app.state.session_factory() as session:
        return session.scalar(select(User).where(User.email == email))


def get_aircraft(app, registration: str):
    from app.db.models import Aircraft

    with app.state.session_factory() as session:
        return session.scalar(select(Aircraft).where(Aircraft.registration == registration))


def get_sortie(app, sortie_number: str) -> Sortie:
    with app.state.session_factory() as session:
        return session.scalar(select(Sortie).where(Sortie.sortie_number == sortie_number))


def create_user(app, *, email: str, role: RoleEnum, base_id: int, full_name: str) -> User:
    with app.state.session_factory() as session:
        user = User(full_name=full_name, email=email, role=role, base_id=base_id)
        session.add(user)
        session.commit()
        session.refresh(user)
        return user


def create_sortie_direct(
    app,
    *,
    sortie_number: str,
    cadet_id: int,
    instructor_id: int,
    aircraft_id: int,
    base_id: int,
    status: SortieStatus = SortieStatus.SCHEDULED,
) -> Sortie:
    now = datetime.now(timezone.utc)
    with app.state.session_factory() as session:
        sortie = Sortie(
            sortie_number=sortie_number,
            cadet_id=cadet_id,
            instructor_id=instructor_id,
            aircraft_id=aircraft_id,
            base_id=base_id,
            lesson_type="Test",
            scheduled_start=now + timedelta(days=2),
            scheduled_end=now + timedelta(days=2, hours=1),
            status=status,
        )
        session.add(sortie)
        session.commit()
        session.refresh(sortie)
        return sortie
