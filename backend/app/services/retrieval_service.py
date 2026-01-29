from dataclasses import dataclass

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy.orm import Session

from app.db.models import DocumentChunk, DocumentPage
from app.db.repos.documents import DocumentRepository


@dataclass(frozen=True)
class RetrievalResult:
    document_id: int
    page_number: int
    chunk_index: int
    snippet: str
    score: float


class RetrievalService:
    def __init__(self, repo: DocumentRepository) -> None:
        self.repo = repo

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

        vectorizer = TfidfVectorizer()
        doc_matrix = vectorizer.fit_transform(texts)
        query_vec = vectorizer.transform([query])
        scores = cosine_similarity(query_vec, doc_matrix).flatten()
        ranked = sorted(range(len(scores)), key=lambda idx: scores[idx], reverse=True)

        results: list[RetrievalResult] = []
        sliced = ranked[offset : offset + top_k]
        for idx in sliced:
            chunk = chunk_meta[idx]
            page = page_map[chunk.page_number]
            snippet = page.text[chunk.start_offset:chunk.end_offset]
            score = float(scores[idx])
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
