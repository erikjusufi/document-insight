from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.repos.documents import DocumentRepository
from app.db.session import get_session
from app.schemas.entities import EntitiesResponse, EntityResponse
from app.services.current_user import get_current_user
from app.services.ner_service import NERService

router = APIRouter()


def get_ner_service() -> NERService:
    return NERService()


@router.get("/documents/{document_id}/entities", response_model=EntitiesResponse)
def list_entities(
    document_id: int,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user),
    ner_service: NERService = Depends(get_ner_service),
) -> EntitiesResponse:
    repo = DocumentRepository()
    document = repo.get_by_id_for_user(session, document_id, current_user.id)
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    pages = repo.list_pages(session, document_id)
    if not pages:
        return EntitiesResponse(document_id=document_id, entities=[])

    full_text = "\n".join(page.text for page in pages)
    entities = ner_service.extract(full_text, document.language)
    return EntitiesResponse(
        document_id=document_id,
        entities=[EntityResponse(text=e.text, label=e.label) for e in entities],
    )
