from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.logging import configure_logging
from app.core.settings import get_settings
from app.db.init import init_db
from app.routers.auth import router as auth_router
from app.routers.documents import router as documents_router
from app.routers.entities import router as entities_router
from app.routers.qa import router as qa_router
from app.routers.retrieval import router as retrieval_router
from app.routers.upload import router as upload_router


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(title=settings.app_name)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    def on_startup() -> None:
        init_db()
        if settings.qa_load_on_startup:
            from app.services.qa_service import QAService

            qa_service = QAService()
            qa_service.load()
            app.state.qa_service = qa_service

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(auth_router, prefix="/auth", tags=["auth"])
    app.include_router(documents_router, tags=["documents"])
    app.include_router(retrieval_router, tags=["documents"])
    app.include_router(upload_router, tags=["documents"])
    app.include_router(entities_router, tags=["documents"])
    app.include_router(qa_router, tags=["qa"])
    return app


app = create_app()
