# Known Limitations

- Authentication is mock JWT login by email and role.
- The project uses SQLite by default for local execution, but the schema is PostgreSQL-friendly.
- Alembic is configured with an initial schema migration, but autogenerate and production release workflows are still manual.
- Rate limiting and idempotency keys are not implemented.
