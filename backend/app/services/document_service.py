from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.settings import get_settings
from app.db.models import Document
from app.db.repos.documents import DocumentRepository


class DocumentService:
    def __init__(self, repo: DocumentRepository) -> None:
        self.repo = repo

    def save_upload(self, session: Session, user_id: int, upload: UploadFile) -> Document:
        settings = get_settings()
        storage_root = Path(settings.storage_dir)
        storage_root.mkdir(parents=True, exist_ok=True)

        file_id = uuid4().hex
        extension = Path(upload.filename or "upload").suffix
        target_path = storage_root / f"{file_id}{extension}"

        content = upload.file.read()
        target_path.write_bytes(content)

        return self.repo.create(
            session=session,
            user_id=user_id,
            filename=upload.filename or "upload",
            content_type=upload.content_type or "application/octet-stream",
            file_path=str(target_path),
            size_bytes=len(content),
        )
