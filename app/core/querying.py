from __future__ import annotations

from sqlalchemy.sql import Select


def apply_pagination(statement: Select, *, page: int, page_size: int) -> Select:
    offset = (page - 1) * page_size
    return statement.offset(offset).limit(page_size)


def ilike_term(value: str) -> str:
    return f"%{value.strip()}%"

