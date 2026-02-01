from pathlib import Path
from uuid import uuid4

import fitz
from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.settings import get_settings
from app.db.models import Document
from app.db.repos.documents import DocumentRepository
from app.services.language_service import LanguageService


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

    def _detect_language(self, upload: UploadFile, path: Path) -> str | None:
        content_type = upload.content_type or ""
        if content_type.startswith("application/pdf"):
            try:
                with fitz.open(path) as pdf:
                    if pdf.page_count:
                        text = pdf.load_page(0).get_text("text")
                    else:
                        text = ""
            except Exception:
                return None
            return self.language_service.detect_language(text)
        if content_type.startswith("text/"):
            try:
                text = path.read_text(encoding="utf-8")
            except Exception:
                return None
            return self.language_service.detect_language(text)
        return None
