from pathlib import Path

import fitz
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.settings import get_settings
from app.db.base import Base
from app.db.models import DocumentChunk, DocumentPage
from app.db.repos.documents import DocumentRepository
from app.db.session import get_engine, get_session
from app.main import create_app
from app.services.document_service import DocumentService


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


def register_and_login(client: TestClient) -> str:
    client.post(
        "/auth/register",
        json={"email": "library@example.com", "password": "secret123"},
    )
    login_response = client.post(
        "/auth/login",
        json={"email": "library@example.com", "password": "secret123"},
    )
    return login_response.json()["access_token"]


def create_pdf(path: Path, text: str) -> None:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text)
    doc.save(path)
    doc.close()


def test_register_and_login_auto_import_sample_docs(client: TestClient, tmp_path: Path) -> None:
    sample_pdf = tmp_path / "samples" / "sample-import.pdf"
    create_pdf(sample_pdf, "Sample content for auto import.")

    token = register_and_login(client)

    list_response = client.get(
        "/documents",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert list_response.status_code == 200
    payload = list_response.json()
    assert len(payload) == 1
    assert payload[0]["filename"] == "sample-import.pdf"
    assert payload[0]["extraction_status"] == "pending"

    client.post(
        "/auth/login",
        json={"email": "library@example.com", "password": "secret123"},
    )
    list_response_after = client.get(
        "/documents",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert list_response_after.status_code == 200
    assert len(list_response_after.json()) == 1


def test_documents_list_includes_extraction_status(client: TestClient) -> None:
    token = register_and_login(client)

    SessionLocal = client.app.state.sessionmaker
    repo = DocumentRepository()
    with SessionLocal() as session:
        user_id = session.execute(
            text("SELECT id FROM users WHERE email = :email"),
            {"email": "library@example.com"},
        ).one()[0]
        document = repo.create(
            session,
            user_id=user_id,
            filename="manual.pdf",
            content_type="application/pdf",
            file_path="/tmp/manual.pdf",
            size_bytes=123,
        )
        document_id = document.id

    pending_response = client.get(
        "/documents",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert pending_response.status_code == 200
    pending_payload = pending_response.json()
    pending_doc = next(doc for doc in pending_payload if doc["id"] == document_id)
    assert pending_doc["extraction_status"] == "pending"
    assert pending_doc["pages_count"] == 0
    assert pending_doc["chunks_count"] == 0

    with SessionLocal() as session:
        page_text = "alpha beta gamma"
        page = DocumentPage(document_id=document_id, page_number=1, text=page_text)
        chunk = DocumentChunk(
            document_id=document_id,
            page_number=1,
            chunk_index=0,
            start_offset=0,
            end_offset=len(page_text),
        )
        repo.replace_pages_and_chunks(session, document_id, [page], [chunk])

    extracted_response = client.get(
        "/documents",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert extracted_response.status_code == 200
    extracted_payload = extracted_response.json()
    extracted_doc = next(doc for doc in extracted_payload if doc["id"] == document_id)
    assert extracted_doc["extraction_status"] == "extracted"
    assert extracted_doc["pages_count"] == 1
    assert extracted_doc["chunks_count"] == 1


def test_documents_list_requires_auth(client: TestClient) -> None:
    response = client.get("/documents")
    assert response.status_code == 401


def test_documents_list_imports_samples_for_existing_token(client: TestClient, tmp_path: Path) -> None:
    sample_pdf = tmp_path / "samples" / "sample-refresh.pdf"
    create_pdf(sample_pdf, "Sample text")
    token = register_and_login(client)

    SessionLocal = client.app.state.sessionmaker
    with SessionLocal() as session:
        user_id = session.execute(
            text("SELECT id FROM users WHERE email = :email"),
            {"email": "library@example.com"},
        ).one()[0]
        session.execute(text("DELETE FROM documents WHERE user_id = :user_id"), {"user_id": user_id})
        session.commit()

    response = client.get(
        "/documents",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert any(doc["filename"] == "sample-refresh.pdf" for doc in payload)


def test_sample_dir_falls_back_when_configured_path_missing(tmp_path: Path) -> None:
    get_settings.cache_clear()
    settings = get_settings()
    settings.sample_docs_dir = str(tmp_path / "does-not-exist")
    service = DocumentService(DocumentRepository())

    resolved = service._resolve_sample_dir()

    assert resolved.name == "samples"
