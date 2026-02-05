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
from app.routers.documents import get_extraction_service
from app.routers.qa import get_ner_service, get_qa_service
from app.services.extraction_service import ExtractionService
from app.services.qa_service import QAAnswer, QAService
from app.services.ner_service import Entity, NERService


class FakeQAService(QAService):
    def __init__(self) -> None:
        pass

    def answer(self, question: str, context: str, model_preset: str | None = None) -> QAAnswer:
        return QAAnswer(answer="sample answer", score=0.9)

    def best_answer(
        self, question: str, contexts: list[str], model_preset: str | None = None
    ) -> QAAnswer:
        return QAAnswer(answer="sample answer", score=0.9)


class FakeNERService(NERService):
    def __init__(self) -> None:
        pass

    def extract(self, text: str, language: str | None = None) -> list[Entity]:
        return []


class FakeExtractionService(ExtractionService):
    def __init__(self, repo: DocumentRepository) -> None:
        self.repo = repo

    def extract_from_document(self, session, document, progress=None):
        if progress:
            progress(1, 1)
        return 1, 1


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
    app.dependency_overrides[get_qa_service] = lambda: FakeQAService()
    app.dependency_overrides[get_ner_service] = lambda: FakeNERService()
    app.dependency_overrides[get_extraction_service] = lambda: FakeExtractionService(
        DocumentRepository()
    )

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def register_and_login(client: TestClient) -> str:
    client.post(
        "/auth/register",
        json={"email": "jobs@example.com", "password": "secret123"},
    )
    login_response = client.post(
        "/auth/login",
        json={"email": "jobs@example.com", "password": "secret123"},
    )
    return login_response.json()["access_token"]


def create_document(client: TestClient) -> int:
    SessionLocal = client.app.state.sessionmaker
    repo = DocumentRepository()
    with SessionLocal() as session:
        user_id = session.execute(
            text("SELECT id FROM users WHERE email = :email"),
            {"email": "jobs@example.com"},
        ).one()[0]
        document = repo.create(
            session,
            user_id=user_id,
            filename="doc.pdf",
            content_type="application/pdf",
            file_path="/tmp/doc.pdf",
            size_bytes=10,
        )
        page_text = "alpha beta gamma"
        page = DocumentPage(document_id=document.id, page_number=1, text=page_text)
        chunk = DocumentChunk(
            document_id=document.id,
            page_number=1,
            chunk_index=0,
            start_offset=0,
            end_offset=len(page_text),
        )
        repo.replace_pages_and_chunks(session, document.id, [page], [chunk])
        return document.id


def test_extract_async_job_completes(client: TestClient) -> None:
    token = register_and_login(client)
    document_id = create_document(client)

    response = client.post(
        f"/documents/{document_id}/extract/async",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    job_id = response.json()["job_id"]

    status_response = client.get(
        f"/jobs/{job_id}", headers={"Authorization": f"Bearer {token}"}
    )
    assert status_response.status_code == 200
    payload = status_response.json()
    assert payload["status"] in {"running", "completed"}


def test_ask_async_job_returns_result(client: TestClient) -> None:
    token = register_and_login(client)
    document_id = create_document(client)

    response = client.post(
        "/ask/async",
        headers={"Authorization": f"Bearer {token}"},
        json={"document_id": document_id, "question": "q", "top_k": 1},
    )

    assert response.status_code == 200
    job_id = response.json()["job_id"]

    status_response = client.get(
        f"/jobs/{job_id}", headers={"Authorization": f"Bearer {token}"}
    )
    assert status_response.status_code == 200
    payload = status_response.json()
    if payload["status"] == "completed":
        assert payload["result"]["answer"] == "sample answer"
