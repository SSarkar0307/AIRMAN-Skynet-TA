from __future__ import annotations

from collections.abc import Generator
from fastapi import Request

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings


class Base(DeclarativeBase):
    pass


def create_db_engine(database_url: str | None = None) -> Engine:
    url = database_url or settings.database_url
    connect_args = {}
    kwargs = {"future": True}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
        kwargs["poolclass"] = StaticPool if ":memory:" in url else None
    if connect_args:
        kwargs["connect_args"] = connect_args
    kwargs = {key: value for key, value in kwargs.items() if value is not None}
    return create_engine(url, **kwargs)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db(request: Request) -> Generator[Session, None, None]:
    session_factory = request.app.state.session_factory
    db = session_factory()
    try:
        yield db
    finally:
        db.close()


def init_db(engine: Engine) -> None:
    from app.db import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
