from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.db.models import DocumentChunk, DocumentPage
from app.db.repos.documents import DocumentRepository
from app.services.embedding_service import EmbeddingService
from app.services.faiss_service import FaissService


@dataclass(frozen=True)
class RetrievalResult:
    document_id: int
    page_number: int
    chunk_index: int
    snippet: str
    score: float


class RetrievalService:
    def __init__(
        self,
        repo: DocumentRepository,
        embedding_service: EmbeddingService | None = None,
        faiss_service: FaissService | None = None,
    ) -> None:
        self.repo = repo
        self.embedding_service = embedding_service or EmbeddingService()
        self.faiss_service = faiss_service or FaissService()

    def retrieve(
        self,
        session: Session,
        document_id: int,
        query: str,
        top_k: int = 3,
        min_score: float = 0.0,
        offset: int = 0,
    ) -> list[RetrievalResult]:
        if not query.strip():
            return []
        pages = self.repo.list_pages(session, document_id)
        chunks = self.repo.list_chunks(session, document_id)
        if not pages or not chunks:
            return []

        page_map = {page.page_number: page for page in pages}
        texts: list[str] = []
        chunk_meta: list[DocumentChunk] = []
        for chunk in chunks:
            page = page_map.get(chunk.page_number)
            if not page:
                continue
            snippet = page.text[chunk.start_offset:chunk.end_offset]
            texts.append(snippet)
            chunk_meta.append(chunk)

        if not texts:
            return []

        chunk_by_id = {chunk.id: chunk for chunk in chunk_meta}
        index, ids = self.faiss_service.load_index(document_id)
        if index is None or len(ids) != len(texts):
            vectors = self.embedding_service.embed_texts(texts)
            ids = [chunk.id for chunk in chunk_meta]
            self.faiss_service.save_index(document_id, vectors, ids)

        query_vector = self.embedding_service.embed_query(query)
        scored = self.faiss_service.search(document_id, query_vector, top_k + offset)

        results: list[RetrievalResult] = []
        for chunk_id, score in scored[offset : offset + top_k]:
            chunk = chunk_by_id.get(chunk_id)
            if chunk is None:
                continue
            page = page_map[chunk.page_number]
            snippet = page.text[chunk.start_offset:chunk.end_offset]
            if score < min_score:
                continue
            results.append(
                RetrievalResult(
                    document_id=document_id,
                    page_number=chunk.page_number,
                    chunk_index=chunk.chunk_index,
                    snippet=snippet,
                    score=score,
                )
            )
        return results
