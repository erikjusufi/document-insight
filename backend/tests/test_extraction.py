from pathlib import Path

import fitz
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.settings import get_settings
from app.db.base import Base
from app.db.repos.documents import DocumentRepository
from app.db.session import get_engine, get_session
from app.main import create_app


@pytest.fixture()
def client(tmp_path: Path):
    db_path = tmp_path / "test.db"
    storage_dir = tmp_path / "storage"
    sample_dir = tmp_path / "samples"
    sample_dir.mkdir(parents=True, exist_ok=True)

    get_settings.cache_clear()
    settings = get_settings()
    settings.database_url = f"sqlite:///{db_path}"
    settings.storage_dir = str(storage_dir)
    settings.sample_docs_dir = str(sample_dir)
    settings.qa_load_on_startup = False

    get_engine.cache_clear()

    app = create_app()

    engine = create_engine(settings.database_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    app.state.sessionmaker = SessionLocal

    def override_get_session():
        with SessionLocal() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def create_sample_pdf(path: Path) -> None:
    doc = fitz.open()
    page1 = doc.new_page()
    page1.insert_text((72, 72), "Hello page one. " * 10)
    page2 = doc.new_page()
    page2.insert_text((72, 72), "Hello page two. " * 10)
    doc.save(path)
    doc.close()


def register_and_login(client: TestClient) -> str:
    client.post(
        "/auth/register",
        json={"email": "extract@example.com", "password": "secret123"},
    )
    login_response = client.post(
        "/auth/login",
        json={"email": "extract@example.com", "password": "secret123"},
    )
    return login_response.json()["access_token"]


def test_extract_pdf_pages_and_chunks(client: TestClient, tmp_path: Path) -> None:
    pdf_path = tmp_path / "sample.pdf"
    create_sample_pdf(pdf_path)

    token = register_and_login(client)

    SessionLocal = client.app.state.sessionmaker
    repo = DocumentRepository()
    with SessionLocal() as session:
        user_id = session.execute(
            text("SELECT id FROM users WHERE email = :email"),
            {"email": "extract@example.com"},
        ).one()[0]
        document = repo.create(
            session,
            user_id=user_id,
            filename="sample.pdf",
            content_type="application/pdf",
            file_path=str(pdf_path),
            size_bytes=pdf_path.stat().st_size,
        )
        document_id = document.id

    response = client.post(
        f"/documents/{document_id}/extract",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["pages_extracted"] == 2
    assert payload["chunks_created"] == 2

    with SessionLocal() as session:
        page_rows = session.execute(
            text("SELECT page_number, text FROM document_pages WHERE document_id = :doc"),
            {"doc": document_id},
        ).all()
        chunk_rows = session.execute(
            text(
                "SELECT page_number, chunk_index, start_offset, end_offset "
                "FROM document_chunks WHERE document_id = :doc"
            ),
            {"doc": document_id},
        ).all()

    assert len(page_rows) == 2
    assert any("Hello page one." in row[1] for row in page_rows)
    assert any("Hello page two." in row[1] for row in page_rows)
    assert len(chunk_rows) == 2
    assert all(row[2] < row[3] for row in chunk_rows)
