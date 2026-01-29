from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.repos.documents import DocumentRepository
from app.db.session import get_session
from app.schemas.extraction import ExtractionResponse
from app.services.current_user import get_current_user
from app.services.extraction_service import ExtractionService

router = APIRouter()


def get_extraction_service() -> ExtractionService:
    return ExtractionService(DocumentRepository())


@router.post("/documents/{document_id}/extract", response_model=ExtractionResponse)
def extract_document(
    document_id: int,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user),
    service: ExtractionService = Depends(get_extraction_service),
) -> ExtractionResponse:
    repo = service.repo
    document = repo.get_by_id_for_user(session, document_id, current_user.id)
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    pages, chunks = service.extract_from_document(session, document)
    return ExtractionResponse(document_id=document.id, pages_extracted=pages, chunks_created=chunks)
