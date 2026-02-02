from sqlalchemy import text

from app.db.base import Base
from app.db.session import get_engine


def _has_column(engine, table_name: str, column_name: str) -> bool:
    with engine.connect() as conn:
        rows = conn.execute(text(f"PRAGMA table_info({table_name})")).fetchall()
    return any(row[1] == column_name for row in rows)


def _add_column(engine, table_name: str, column_def: str) -> None:
    with engine.begin() as conn:
        conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_def}"))


def init_db() -> None:
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    if not _has_column(engine, "documents", "language"):
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE documents ADD COLUMN language VARCHAR(16)"))
    chunks_changed = False
    if not _has_column(engine, "document_chunks", "start_offset"):
        _add_column(engine, "document_chunks", "start_offset INTEGER DEFAULT 0")
        chunks_changed = True
    if not _has_column(engine, "document_chunks", "end_offset"):
        _add_column(engine, "document_chunks", "end_offset INTEGER DEFAULT 0")
        chunks_changed = True
    if chunks_changed:
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    UPDATE document_chunks
                    SET start_offset = COALESCE(start_offset, 0),
                        end_offset = COALESCE(
                            NULLIF(end_offset, 0),
                            (
                                SELECT LENGTH(text)
                                FROM document_pages
                                WHERE document_pages.document_id = document_chunks.document_id
                                  AND document_pages.page_number = document_chunks.page_number
                            )
                        )
                    """
                )
            )
