from sqlalchemy import text

from app.core.settings import get_settings
from app.db.init import init_db
from app.db.session import get_engine


def test_init_db_adds_chunk_offsets(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    get_settings.cache_clear()
    get_engine.cache_clear()

    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE documents (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER,
                    filename TEXT,
                    content_type TEXT,
                    file_path TEXT,
                    size_bytes INTEGER
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE document_pages (
                    id INTEGER PRIMARY KEY,
                    document_id INTEGER,
                    page_number INTEGER,
                    text TEXT
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE document_chunks (
                    id INTEGER PRIMARY KEY,
                    document_id INTEGER,
                    page_number INTEGER,
                    chunk_index INTEGER
                )
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO document_pages (id, document_id, page_number, text)
                VALUES (1, 1, 1, 'hello world')
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO document_chunks (id, document_id, page_number, chunk_index)
                VALUES (1, 1, 1, 0)
                """
            )
        )

    init_db()

    with engine.connect() as conn:
        columns = [row[1] for row in conn.execute(text("PRAGMA table_info(document_chunks)"))]
        assert "start_offset" in columns
        assert "end_offset" in columns
        row = conn.execute(
            text("SELECT start_offset, end_offset FROM document_chunks WHERE id = 1")
        ).fetchone()
        assert row is not None
        assert row[0] == 0
        assert row[1] == len("hello world")

        doc_columns = [
            row[1] for row in conn.execute(text("PRAGMA table_info(documents)"))
        ]
        assert "language" in doc_columns
