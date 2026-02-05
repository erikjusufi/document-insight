from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.settings import get_settings
from app.db.base import Base
from app.db.models import DocumentPage
from app.db.repos.documents import DocumentRepository
from app.db.session import get_engine, get_session
from app.main import create_app
from app.routers.entities import get_ner_service
from app.services.ner_service import Entity, NERService


class FakeNERService(NERService):
    def __init__(self) -> None:
        pass

    def extract(self, text: str, language: str | None = None) -> list[Entity]:
        return [Entity(text="Zagreb", label="GPE")]


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
    app.dependency_overrides[get_ner_service] = lambda: FakeNERService()

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def register_and_login(client: TestClient) -> str:
    client.post(
        "/auth/register",
        json={"email": "ner@example.com", "password": "secret123"},
    )
    login_response = client.post(
        "/auth/login",
        json={"email": "ner@example.com", "password": "secret123"},
    )
    return login_response.json()["access_token"]


def test_entities_endpoint_returns_entities(client: TestClient) -> None:
    token = register_and_login(client)

    SessionLocal = client.app.state.sessionmaker
    repo = DocumentRepository()
    with SessionLocal() as session:
        user_id = session.execute(
            text("SELECT id FROM users WHERE email = :email"),
            {"email": "ner@example.com"},
        ).one()[0]
        document = repo.create(
            session,
            user_id=user_id,
            filename="doc.pdf",
            content_type="application/pdf",
            file_path="/tmp/doc.pdf",
            size_bytes=10,
        )
        page = DocumentPage(document_id=document.id, page_number=1, text="Zagreb is capital")
        repo.replace_pages_and_chunks(session, document.id, [page], [])
        document_id = document.id

    response = client.get(
        f"/documents/{document_id}/entities",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["document_id"] == document_id
    assert payload["entities"][0]["text"] == "Zagreb"


def test_entities_requires_auth(client: TestClient) -> None:
    response = client.get("/documents/1/entities")
    assert response.status_code == 401
