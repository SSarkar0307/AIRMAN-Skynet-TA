from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    app_name: str = "Skynet Flight Operations API"
    app_version: str = os.getenv("APP_VERSION", "1.0.0")
    app_description: str = (
        "Backend-only aviation operations platform for training academies. "
        "Implements sortie workflow control, training approval, aircraft readiness, "
        "defect handling, RBAC, base scoping, and audit logging."
    )
    database_url: str = os.getenv("DATABASE_URL", "sqlite+pysqlite:///./airman.db")
    jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", "dev-secret-change-me")
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "120"))
    api_version: str = os.getenv("API_VERSION", "v1")
    database_connect_retries: int = int(os.getenv("DATABASE_CONNECT_RETRIES", "5"))
    database_connect_retry_delay_seconds: float = float(os.getenv("DATABASE_CONNECT_RETRY_DELAY_SECONDS", "2"))


settings = Settings()
