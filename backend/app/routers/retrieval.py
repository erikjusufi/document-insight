from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.repos.documents import DocumentRepository
from app.db.session import get_session
from app.schemas.retrieval import RetrievalRequest, RetrievalResponse, RetrievalResultResponse
from app.services.current_user import get_current_user
from app.services.embedding_service import EmbeddingService
from app.services.faiss_service import FaissService
from app.services.retrieval_service import RetrievalService

router = APIRouter()


def get_retrieval_service() -> RetrievalService:
    return RetrievalService(
        DocumentRepository(),
        embedding_service=EmbeddingService(),
        faiss_service=FaissService(),
    )


@router.post("/documents/{document_id}/search", response_model=RetrievalResponse)
def search_document(
    document_id: int,
    payload: RetrievalRequest,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user),
    service: RetrievalService = Depends(get_retrieval_service),
) -> RetrievalResponse:
    document = service.repo.get_by_id_for_user(session, document_id, current_user.id)
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    results = service.retrieve(
        session,
        document_id,
        payload.query,
        top_k=payload.top_k,
        min_score=payload.min_score,
        offset=payload.offset,
    )
    return RetrievalResponse(
        document_id=document_id,
        results=[
            RetrievalResultResponse(
                page_number=result.page_number,
                chunk_index=result.chunk_index,
                snippet=result.snippet,
                score=result.score,
            )
            for result in results
        ],
    )
