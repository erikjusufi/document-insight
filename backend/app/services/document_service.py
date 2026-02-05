import shutil
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

import fitz
from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.settings import get_settings
from app.db.models import Document
from app.db.repos.documents import DocumentRepository
from app.services.language_service import LanguageService


@dataclass(frozen=True)
class DocumentLibraryItem:
    document: Document
    pages_count: int
    chunks_count: int

    @property
    def extraction_status(self) -> str:
        return "extracted" if self.pages_count > 0 else "pending"


class DocumentService:
    def __init__(
        self,
        repo: DocumentRepository,
        language_service: LanguageService | None = None,
    ) -> None:
        self.repo = repo
        self.language_service = language_service or LanguageService()

    def save_upload(self, session: Session, user_id: int, upload: UploadFile) -> Document:
        settings = get_settings()
        storage_root = Path(settings.storage_dir)
        storage_root.mkdir(parents=True, exist_ok=True)

        file_id = uuid4().hex
        extension = Path(upload.filename or "upload").suffix
        target_path = storage_root / f"{file_id}{extension}"

        content = upload.file.read()
        target_path.write_bytes(content)

        language = self._detect_language(upload, target_path)

        return self.repo.create(
            session=session,
            user_id=user_id,
            filename=upload.filename or "upload",
            content_type=upload.content_type or "application/octet-stream",
            file_path=str(target_path),
            size_bytes=len(content),
            language=language,
        )

    def list_documents_for_user(self, session: Session, user_id: int) -> list[DocumentLibraryItem]:
        rows = self.repo.list_for_user_with_stats(session, user_id)
        return [
            DocumentLibraryItem(
                document=document,
                pages_count=pages_count,
                chunks_count=chunks_count,
            )
            for document, pages_count, chunks_count in rows
        ]

    def import_sample_documents(self, session: Session, user_id: int) -> int:
        sample_dir = self._resolve_sample_dir()
        if not sample_dir.exists() or not sample_dir.is_dir():
            return 0

        created = 0
        settings = get_settings()
        storage_root = Path(settings.storage_dir)
        storage_root.mkdir(parents=True, exist_ok=True)

        for sample_path in sorted(sample_dir.glob("*.pdf")):
            size_bytes = sample_path.stat().st_size
            existing = self.repo.get_by_user_filename_and_size(
                session=session,
                user_id=user_id,
                filename=sample_path.name,
                size_bytes=size_bytes,
            )
            if existing:
                continue

            target_path = storage_root / f"{uuid4().hex}{sample_path.suffix}"
            shutil.copyfile(sample_path, target_path)
            language = self._detect_language_for_pdf(target_path)
            self.repo.create(
                session=session,
                user_id=user_id,
                filename=sample_path.name,
                content_type="application/pdf",
                file_path=str(target_path),
                size_bytes=size_bytes,
                language=language,
            )
            created += 1
        return created

    def _detect_language(self, upload: UploadFile, path: Path) -> str | None:
        content_type = upload.content_type or ""
        if content_type.startswith("application/pdf"):
            return self._detect_language_for_pdf(path)
        if content_type.startswith("text/"):
            try:
                text = path.read_text(encoding="utf-8")
            except Exception:
                return None
            return self.language_service.detect_language(text)
        return None

    def _resolve_sample_dir(self) -> Path:
        settings = get_settings()
        configured = Path(settings.sample_docs_dir).resolve()
        if configured.exists():
            return configured
        return Path(__file__).resolve().parents[3] / "samples"

    def _detect_language_for_pdf(self, path: Path) -> str | None:
        try:
            with fitz.open(path) as pdf:
                text = pdf.load_page(0).get_text("text") if pdf.page_count else ""
        except Exception:
            return None
        return self.language_service.detect_language(text)
