from sqlalchemy import text

from app.db.base import Base
from app.db.models import DocumentChunk
from app.db.session import get_engine


def _has_column(engine, table_name: str, column_name: str) -> bool:
    with engine.connect() as conn:
        rows = conn.execute(text(f"PRAGMA table_info({table_name})")).fetchall()
    return any(row[1] == column_name for row in rows)


def _recreate_chunks_table(engine) -> None:
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS document_chunks"))
    DocumentChunk.__table__.create(bind=engine)


def init_db() -> None:
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    if not _has_column(engine, "document_chunks", "start_offset"):
        _recreate_chunks_table(engine)
