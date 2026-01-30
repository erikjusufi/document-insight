from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.models import DocumentChunk, DocumentPage
from app.db.repos.documents import DocumentRepository
from app.services.faiss_service import FaissService
from app.services.retrieval_service import RetrievalService


class FakeEmbeddingService:
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [[float(len(text))] for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return [float(len(text))]


@pytest.fixture()
def session(tmp_path: Path):
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with SessionLocal() as session:
        yield session


def test_retrieval_returns_relevant_chunk(session, tmp_path: Path):
    repo = DocumentRepository()

    doc = repo.create(
        session,
        user_id=1,
        filename="doc.pdf",
        content_type="application/pdf",
        file_path="/tmp/doc.pdf",
        size_bytes=10,
    )

    page_text = "alpha beta gamma delta epsilon zebra tiger"
    page = DocumentPage(document_id=doc.id, page_number=1, text=page_text)
    chunk = DocumentChunk(
        document_id=doc.id,
        page_number=1,
        chunk_index=0,
        start_offset=0,
        end_offset=len(page_text),
    )
    repo.replace_pages_and_chunks(session, doc.id, [page], [chunk])

    faiss_service = FaissService(index_dir=str(tmp_path / "faiss"))
    service = RetrievalService(
        repo,
        embedding_service=FakeEmbeddingService(),
        faiss_service=faiss_service,
    )
    results = service.retrieve(session, doc.id, "zebra", top_k=1)

    assert len(results) == 1
    assert "zebra" in results[0].snippet


def test_retrieval_empty_query_returns_no_results(session, tmp_path: Path):
    repo = DocumentRepository()

    doc = repo.create(
        session,
        user_id=1,
        filename="doc.pdf",
        content_type="application/pdf",
        file_path="/tmp/doc.pdf",
        size_bytes=10,
    )

    page_text = "alpha beta gamma delta epsilon zebra tiger"
    page = DocumentPage(document_id=doc.id, page_number=1, text=page_text)
    chunk = DocumentChunk(
        document_id=doc.id,
        page_number=1,
        chunk_index=0,
        start_offset=0,
        end_offset=len(page_text),
    )
    repo.replace_pages_and_chunks(session, doc.id, [page], [chunk])

    faiss_service = FaissService(index_dir=str(tmp_path / "faiss"))
    service = RetrievalService(
        repo,
        embedding_service=FakeEmbeddingService(),
        faiss_service=faiss_service,
    )
    results = service.retrieve(session, doc.id, "   ", top_k=1)

    assert results == []
