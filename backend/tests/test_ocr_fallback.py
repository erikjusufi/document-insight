from pathlib import Path
from unittest.mock import MagicMock

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
from app.services.extraction_service import ExtractionService


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


def create_blank_pdf(path: Path) -> None:
    doc = fitz.open()
    doc.new_page()
    doc.save(path)
    doc.close()


def register_and_login(client: TestClient) -> str:
    client.post(
        "/auth/register",
        json={"email": "ocr@example.com", "password": "secret123"},
    )
    login_response = client.post(
        "/auth/login",
        json={"email": "ocr@example.com", "password": "secret123"},
    )
    return login_response.json()["access_token"]


def test_ocr_fallback_on_empty_page(client: TestClient, tmp_path: Path, monkeypatch) -> None:
    pdf_path = tmp_path / "blank.pdf"
    create_blank_pdf(pdf_path)

    token = register_and_login(client)

    SessionLocal = client.app.state.sessionmaker
    repo = DocumentRepository()
    with SessionLocal() as session:
        user_id = session.execute(
            text("SELECT id FROM users WHERE email = :email"),
            {"email": "ocr@example.com"},
        ).one()[0]
        document = repo.create(
            session,
            user_id=user_id,
            filename="blank.pdf",
            content_type="application/pdf",
            file_path=str(pdf_path),
            size_bytes=pdf_path.stat().st_size,
        )
        document_id = document.id

    ocr_mock = MagicMock()
    ocr_mock.extract_text_from_image.return_value = "OCR text"
    monkeypatch.setattr(
        "app.services.extraction_service.OCRService",
        lambda: ocr_mock,
    )

    response = client.post(
        f"/documents/{document_id}/extract",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert ocr_mock.extract_text_from_image.called

    with SessionLocal() as session:
        page_text = session.execute(
            text("SELECT text FROM document_pages WHERE document_id = :doc"),
            {"doc": document_id},
        ).one()[0]
    assert page_text == "OCR text"


def test_ocr_for_image_upload(client: TestClient, tmp_path: Path, monkeypatch) -> None:
    image_path = tmp_path / "sample.png"
    image_path.write_bytes(b"fake")

    token = register_and_login(client)

    SessionLocal = client.app.state.sessionmaker
    repo = DocumentRepository()
    with SessionLocal() as session:
        user_id = session.execute(
            text("SELECT id FROM users WHERE email = :email"),
            {"email": "ocr@example.com"},
        ).one()[0]
        document = repo.create(
            session,
            user_id=user_id,
            filename="sample.png",
            content_type="image/png",
            file_path=str(image_path),
            size_bytes=image_path.stat().st_size,
        )
        document_id = document.id

    ocr_mock = MagicMock()
    ocr_mock.extract_text_from_image.return_value = "Image OCR"
    monkeypatch.setattr(
        "app.services.extraction_service.OCRService",
        lambda: ocr_mock,
    )

    response = client.post(
        f"/documents/{document_id}/extract",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert ocr_mock.extract_text_from_image.called

    with SessionLocal() as session:
        page_text = session.execute(
            text("SELECT text FROM document_pages WHERE document_id = :doc"),
            {"doc": document_id},
        ).one()[0]
    assert page_text == "Image OCR"
