from pathlib import Path

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
from app.routers.retrieval import get_retrieval_service
from app.services.retrieval_service import RetrievalService


class FakeEmbeddingService:
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [[float(len(text))] for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return [float(len(text))]


@pytest.fixture()
def client(tmp_path: Path):
    db_path = tmp_path / "test.db"
    storage_dir = tmp_path / "storage"

    get_settings.cache_clear()
    settings = get_settings()
    settings.database_url = f"sqlite:///{db_path}"
    settings.storage_dir = str(storage_dir)
    settings.qa_load_on_startup = False
    settings.faiss_index_dir = str(tmp_path / "faiss")

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
    app.dependency_overrides[get_retrieval_service] = lambda: RetrievalService(
        DocumentRepository(),
        embedding_service=FakeEmbeddingService(),
    )

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def register_and_login(client: TestClient) -> str:
    client.post(
        "/auth/register",
        json={"email": "search@example.com", "password": "secret123"},
    )
    login_response = client.post(
        "/auth/login",
        json={"email": "search@example.com", "password": "secret123"},
    )
    return login_response.json()["access_token"]


def test_search_endpoint_returns_results(client: TestClient) -> None:
    token = register_and_login(client)

    SessionLocal = client.app.state.sessionmaker
    repo = DocumentRepository()
    with SessionLocal() as session:
        user_id = session.execute(
            text("SELECT id FROM users WHERE email = :email"),
            {"email": "search@example.com"},
        ).one()[0]
        document = repo.create(
            session,
            user_id=user_id,
            filename="doc.pdf",
            content_type="application/pdf",
            file_path="/tmp/doc.pdf",
            size_bytes=10,
        )
        page_text = "alpha beta gamma delta epsilon zebra tiger"
        page = DocumentPage(document_id=document.id, page_number=1, text=page_text)
        chunk = DocumentChunk(
            document_id=document.id,
            page_number=1,
            chunk_index=0,
            start_offset=0,
            end_offset=len(page_text),
        )
        repo.replace_pages_and_chunks(session, document.id, [page], [chunk])
        document_id = document.id

    response = client.post(
        f"/documents/{document_id}/search",
        headers={"Authorization": f"Bearer {token}"},
        json={"query": "zebra", "top_k": 1, "min_score": 0.0, "offset": 0},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["document_id"] == document_id
    assert payload["results"][0]["page_number"] == 1
    assert "zebra" in payload["results"][0]["snippet"]


def test_search_endpoint_min_score_filters(client: TestClient) -> None:
    token = register_and_login(client)

    SessionLocal = client.app.state.sessionmaker
    repo = DocumentRepository()
    with SessionLocal() as session:
        user_id = session.execute(
            text("SELECT id FROM users WHERE email = :email"),
            {"email": "search@example.com"},
        ).one()[0]
        document = repo.create(
            session,
            user_id=user_id,
            filename="doc.pdf",
            content_type="application/pdf",
            file_path="/tmp/doc.pdf",
            size_bytes=10,
        )
        page_text = "alpha beta gamma delta epsilon zebra tiger"
        page = DocumentPage(document_id=document.id, page_number=1, text=page_text)
        chunk = DocumentChunk(
            document_id=document.id,
            page_number=1,
            chunk_index=0,
            start_offset=0,
            end_offset=len(page_text),
        )
        repo.replace_pages_and_chunks(session, document.id, [page], [chunk])
        document_id = document.id

    response = client.post(
        f"/documents/{document_id}/search",
        headers={"Authorization": f"Bearer {token}"},
        json={"query": "zebra", "top_k": 1, "min_score": 1000.0, "offset": 0},
    )

    assert response.status_code == 200
    assert response.json()["results"] == []
