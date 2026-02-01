from fastapi import APIRouter, Depends, UploadFile, status
from sqlalchemy.orm import Session

from app.db.repos.documents import DocumentRepository
from app.db.session import get_session
from app.schemas.documents import DocumentResponse
from app.services.current_user import get_current_user
from app.services.document_service import DocumentService

router = APIRouter()


def get_document_service() -> DocumentService:
    return DocumentService(DocumentRepository())


@router.post("/upload", response_model=list[DocumentResponse], status_code=status.HTTP_201_CREATED)
def upload_documents(
    files: list[UploadFile],
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user),
    service: DocumentService = Depends(get_document_service),
) -> list[DocumentResponse]:
    docs = [service.save_upload(session, current_user.id, upload) for upload in files]
    return [
        DocumentResponse(
            id=doc.id,
            filename=doc.filename,
            content_type=doc.content_type,
            size_bytes=doc.size_bytes,
            language=doc.language,
        )
        for doc in docs
    ]
