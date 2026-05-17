from __future__ import annotations

import time

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.api.routes.aircraft import router as aircraft_router
from app.api.routes.audit_logs import router as audit_logs_router
from app.api.routes.auth import router as auth_router
from app.api.routes.bases import router as bases_router
from app.api.routes.defects import router as defects_router
from app.api.routes.health import router as health_router
from app.api.routes.sorties import router as sorties_router
from app.api.routes.training_progress import router as training_router
from app.api.routes.users import router as users_router
from app.core.config import settings
from app.core.errors import AppError
from app.db.database import create_db_engine, create_session_factory, get_db, init_db
from app.db.seed import seed_demo_data

OPENAPI_TAGS = [
    {
        "name": "auth",
        "description": "Mock login and current-user lookup for the assessment environment.",
    },
    {
        "name": "users",
        "description": "User directory endpoints with role-aware and base-scoped access control.",
    },
    {
        "name": "bases",
        "description": "Training base records used to scope aircraft, sorties, and permissions.",
    },
    {
        "name": "aircraft",
        "description": "Aircraft readiness, assignment, and grounding controls.",
    },
    {
        "name": "sorties",
        "description": "Flight dispatch workflow and sortie lifecycle state machine.",
    },
    {
        "name": "training-progress",
        "description": "Instructor evaluation drafting, submission, and CFI approval flow.",
    },
    {
        "name": "defects",
        "description": "Aircraft defect reporting and maintenance resolution/deferment.",
    },
    {
        "name": "audit-logs",
        "description": "Immutable operational history for compliance and traceability.",
    },
    {
        "name": "health",
        "description": "Basic service health probe.",
    },
]


def create_app(database_url: str | None = None) -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=settings.app_description,
        openapi_tags=OPENAPI_TAGS,
    )
    engine = create_db_engine(database_url)
    session_factory = create_session_factory(engine)
    app.state.engine = engine
    app.state.session_factory = session_factory
    for attempt in range(settings.database_connect_retries):
        try:
            init_db(engine)
            with session_factory() as session:
                seed_demo_data(session)
            break
        except OperationalError:
            if attempt >= settings.database_connect_retries - 1:
                raise
            time.sleep(settings.database_connect_retry_delay_seconds)

    app.include_router(auth_router)
    app.include_router(users_router)
    app.include_router(bases_router)
    app.include_router(aircraft_router)
    app.include_router(sorties_router)
    app.include_router(training_router)
    app.include_router(defects_router)
    app.include_router(audit_logs_router)
    app.include_router(health_router)

    @app.exception_handler(AppError)
    def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
        payload = {"error": exc.code, "message": exc.message}
        if exc.field is not None:
            payload["field"] = exc.field
        return JSONResponse(status_code=exc.status_code, content=payload)

    @app.exception_handler(RequestValidationError)
    def validation_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        first = exc.errors()[0] if exc.errors() else {}
        field = ".".join(str(item) for item in first.get("loc", []) if item not in {"body", "query", "path"})
        message = first.get("msg", "Invalid request")
        return JSONResponse(
            status_code=422,
            content={"error": "VALIDATION_ERROR", "message": message, "field": field or None},
        )

    return app


app = create_app()
