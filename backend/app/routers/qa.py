from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.db.repos.documents import DocumentRepository
from app.db.session import get_session
from app.schemas.jobs import JobStatusResponse
from app.schemas.qa import AskEntity, AskRequest, AskResponse, AskSource
from app.core.settings import get_settings
from app.services.current_user import get_current_user
from app.services.qa_service import QAService
from app.services.retrieval_service import RetrievalService
from app.services.ner_service import NERService

router = APIRouter()


def get_qa_service(request: Request) -> QAService:
    if hasattr(request.app.state, "qa_service"):
        return request.app.state.qa_service
    return QAService()


def get_retrieval_service() -> RetrievalService:
    return RetrievalService(DocumentRepository())


def get_ner_service() -> NERService:
    return NERService()


def get_job_store(request: Request):
    if hasattr(request.app.state, "job_store"):
        return request.app.state.job_store
    return None


def build_answer(
    payload: AskRequest,
    session: Session,
    user_id: int,
    qa_service: QAService,
    retrieval_service: RetrievalService,
    ner_service: NERService,
) -> AskResponse:
    settings = get_settings()
    document = retrieval_service.repo.get_by_id_for_user(session, payload.document_id, user_id)
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    retrieval_k = max(payload.top_k, settings.qa_top_k)
    results = retrieval_service.retrieve(
        session,
        payload.document_id,
        payload.question,
        top_k=retrieval_k,
    )
    if not results:
        return AskResponse(answer="", confidence=0.0, sources=[], entities=[])

    max_chars = settings.qa_max_context_chars
    contexts: list[str] = []
    current = ""
    for result in results:
        if len(current) + len(result.snippet) + 2 > max_chars and current:
            contexts.append(current)
            current = ""
        if len(result.snippet) > max_chars:
            contexts.append(result.snippet[:max_chars])
            continue
        current = f"{current}\n\n{result.snippet}" if current else result.snippet
    if current:
        contexts.append(current)

    answer = qa_service.best_answer(payload.question, contexts, model_preset=payload.model_preset)
    sources = [AskSource(page_number=r.page_number, snippet=r.snippet) for r in results[:payload.top_k]]
    combined_text = "\n\n".join(source.snippet for source in sources)
    entities = ner_service.extract(combined_text, document.language)

    return AskResponse(
        answer=answer.answer,
        confidence=answer.score,
        sources=sources,
        entities=[AskEntity(text=e.text, label=e.label) for e in entities],
    )


@router.post("/ask", response_model=AskResponse)
def ask(
    payload: AskRequest,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user),
    qa_service: QAService = Depends(get_qa_service),
    retrieval_service: RetrievalService = Depends(get_retrieval_service),
    ner_service: NERService = Depends(get_ner_service),
) -> AskResponse:
    return build_answer(payload, session, current_user.id, qa_service, retrieval_service, ner_service)


@router.post("/ask/async", response_model=JobStatusResponse)
def ask_async(
    payload: AskRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user),
    qa_service: QAService = Depends(get_qa_service),
    retrieval_service: RetrievalService = Depends(get_retrieval_service),
    ner_service: NERService = Depends(get_ner_service),
) -> JobStatusResponse:
    store = get_job_store(request)
    if store is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Job store not available")
    record = store.create("ask", current_user.id)
    store.update(record.job_id, status="running", stage="retrieving", progress=10)

    def run_ask() -> None:
        from sqlalchemy.orm import sessionmaker

        from app.db.session import get_engine

        try:
            store.update(record.job_id, status="running", stage="retrieving", progress=30)
            SessionLocal = sessionmaker(bind=get_engine(), autoflush=False, autocommit=False)
            with SessionLocal() as async_session:
                response = build_answer(
                    payload,
                    async_session,
                    current_user.id,
                    qa_service,
                    retrieval_service,
                    ner_service,
                )
            store.update(record.job_id, status="running", stage="scoring", progress=70)
            store.update(record.job_id, status="running", stage="entities", progress=90)
            store.complete(record.job_id, result=response.model_dump())
        except Exception as exc:
            store.fail(record.job_id, str(exc))

    background_tasks.add_task(run_ask)

    return JobStatusResponse(
        job_id=record.job_id,
        job_type=record.job_type,
        status=record.status,
        stage=record.stage,
        progress=record.progress,
    )
