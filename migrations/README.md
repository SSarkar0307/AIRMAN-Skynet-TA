# Migrations

This directory contains the Alembic migration environment for the Skynet backend.

Important files:

- `alembic.ini` in the repository root configures the migration runner.
- `migrations/env.py` connects Alembic to the SQLAlchemy metadata in `app.db.models`.
- `migrations/versions/0001_initial_schema.py` creates the full initial schema.

Common commands:

```bash
alembic upgrade head
alembic downgrade -1
alembic revision -m "describe change"
```

In Docker Compose, the app service runs `alembic upgrade head` before starting Uvicorn.
