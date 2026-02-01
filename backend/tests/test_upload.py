from pathlib import Path

import pytest
from fastapi.testclient import TestClient
import fitz
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.settings import get_settings
from app.db.base import Base
from app.db.session import get_engine, get_session
from app.main import create_app


@pytest.fixture()
def client(tmp_path):
    db_path = tmp_path / "test.db"
    storage_dir = tmp_path / "storage"

    get_settings.cache_clear()
    settings = get_settings()
    settings.database_url = f"sqlite:///{db_path}"
    settings.storage_dir = str(storage_dir)
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
        json={"email": "uploader@example.com", "password": "secret123"},
    )
    login_response = client.post(
        "/auth/login",
        json={"email": "uploader@example.com", "password": "secret123"},
    )
    return login_response.json()["access_token"]


def test_upload_requires_auth(client: TestClient) -> None:
    response = client.post("/upload", files={"files": ("file.txt", b"hi")})
    assert response.status_code == 401


def test_upload_saves_files_and_metadata(client: TestClient, tmp_path: Path) -> None:
    token = register_and_login(client)

    response = client.post(
        "/upload",
        headers={"Authorization": f"Bearer {token}"},
        files=[
            ("files", ("a.txt", b"hello", "text/plain")),
            ("files", ("b.txt", b"world", "text/plain")),
        ],
    )

    assert response.status_code == 201
    payload = response.json()
    assert len(payload) == 2
    assert payload[0]["filename"] == "a.txt"
    assert payload[1]["filename"] == "b.txt"

    storage_dir = tmp_path / "storage"
    assert storage_dir.exists()
    assert len(list(storage_dir.iterdir())) == 2

    SessionLocal = client.app.state.sessionmaker
    with SessionLocal() as session:
        rows = session.execute(text("SELECT filename FROM documents")).all()
        filenames = sorted(row[0] for row in rows)
    assert filenames == ["a.txt", "b.txt"]


def test_upload_detects_language_for_pdf(client: TestClient, tmp_path: Path) -> None:
    token = register_and_login(client)

    pdf_path = tmp_path / "lang.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "This is an English sentence. " * 5)
    doc.save(pdf_path)
    doc.close()

    response = client.post(
        "/upload",
        headers={"Authorization": f"Bearer {token}"},
        files=[("files", ("lang.pdf", pdf_path.read_bytes(), "application/pdf"))],
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload[0]["language"] == "en"
