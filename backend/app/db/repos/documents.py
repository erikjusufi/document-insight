from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.models import Document, DocumentChunk, DocumentPage


class DocumentRepository:
    def get_by_id_for_user(self, session: Session, document_id: int, user_id: int) -> Document | None:
        stmt = select(Document).where(Document.id == document_id, Document.user_id == user_id)
        return session.execute(stmt).scalar_one_or_none()

    def create(
        self,
        session: Session,
        user_id: int,
        filename: str,
        content_type: str,
        file_path: str,
        size_bytes: int,
        language: str | None = None,
    ) -> Document:
        doc = Document(
            user_id=user_id,
            filename=filename,
            content_type=content_type,
            file_path=file_path,
            size_bytes=size_bytes,
            language=language,
        )
        session.add(doc)
        session.commit()
        session.refresh(doc)
        return doc

    def update_language(self, session: Session, document: Document, language: str | None) -> Document:
        document.language = language
        session.add(document)
        session.commit()
        session.refresh(document)
        return document

    def replace_pages_and_chunks(
        self,
        session: Session,
        document_id: int,
        pages: list[DocumentPage],
        chunks: list[DocumentChunk],
    ) -> None:
        session.execute(delete(DocumentPage).where(DocumentPage.document_id == document_id))
        session.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document_id))
        session.add_all(pages + chunks)
        session.commit()

    def list_pages(self, session: Session, document_id: int) -> list[DocumentPage]:
        stmt = select(DocumentPage).where(DocumentPage.document_id == document_id)
        return list(session.execute(stmt).scalars().all())

    def list_chunks(self, session: Session, document_id: int) -> list[DocumentChunk]:
        stmt = select(DocumentChunk).where(DocumentChunk.document_id == document_id)
        return list(session.execute(stmt).scalars().all())
