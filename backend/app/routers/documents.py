from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.db.repos.documents import DocumentRepository
from app.db.session import get_session
from app.schemas.extraction import ExtractionResponse
from app.schemas.jobs import JobStatusResponse
from app.services.current_user import get_current_user
from app.services.extraction_service import ExtractionService

router = APIRouter()


def get_extraction_service() -> ExtractionService:
    return ExtractionService(DocumentRepository())


def get_job_store(request: Request):
    if hasattr(request.app.state, "job_store"):
        return request.app.state.job_store
    return None


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


@router.post("/documents/{document_id}/extract/async", response_model=JobStatusResponse)
def extract_document_async(
    document_id: int,
    background_tasks: BackgroundTasks,
    request: Request,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user),
    service: ExtractionService = Depends(get_extraction_service),
) -> JobStatusResponse:
    repo = service.repo
    document = repo.get_by_id_for_user(session, document_id, current_user.id)
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    store = get_job_store(request)
    if store is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Job store not available")

    record = store.create("extraction", current_user.id)
    store.update(record.job_id, status="running", stage="starting", progress=0)

    def run_extraction() -> None:
        from sqlalchemy.orm import sessionmaker

        from app.db.session import get_engine

        def on_progress(current: int, total: int) -> None:
            progress = int((current / max(total, 1)) * 100)
            store.update(record.job_id, status="running", stage="extracting", progress=progress)

        SessionLocal = sessionmaker(bind=get_engine(), autoflush=False, autocommit=False)
        with SessionLocal() as async_session:
            doc = repo.get_by_id_for_user(async_session, document_id, current_user.id)
            if not doc:
                store.fail(record.job_id, "Document not found")
                return
            try:
                pages, chunks = service.extract_from_document(async_session, doc, progress=on_progress)
                store.complete(
                    record.job_id,
                    result={
                        "document_id": doc.id,
                        "pages_extracted": pages,
                        "chunks_created": chunks,
                    },
                )
            except Exception as exc:
                store.fail(record.job_id, str(exc))

    background_tasks.add_task(run_extraction)

    return JobStatusResponse(
        job_id=record.job_id,
        job_type=record.job_type,
        status=record.status,
        stage=record.stage,
        progress=record.progress,
    )
