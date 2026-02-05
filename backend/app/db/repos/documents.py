from sqlalchemy import delete, distinct, func, select
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

    def get_by_user_filename_and_size(
        self,
        session: Session,
        user_id: int,
        filename: str,
        size_bytes: int,
    ) -> Document | None:
        stmt = select(Document).where(
            Document.user_id == user_id,
            Document.filename == filename,
            Document.size_bytes == size_bytes,
        )
        return session.execute(stmt).scalar_one_or_none()

    def list_for_user_with_stats(
        self,
        session: Session,
        user_id: int,
    ) -> list[tuple[Document, int, int]]:
        pages_count = func.count(distinct(DocumentPage.id)).label("pages_count")
        chunks_count = func.count(distinct(DocumentChunk.id)).label("chunks_count")
        stmt = (
            select(Document, pages_count, chunks_count)
            .outerjoin(DocumentPage, DocumentPage.document_id == Document.id)
            .outerjoin(DocumentChunk, DocumentChunk.document_id == Document.id)
            .where(Document.user_id == user_id)
            .group_by(Document.id)
            .order_by(Document.id.desc())
        )
        rows = session.execute(stmt).all()
        return [(row[0], int(row[1] or 0), int(row[2] or 0)) for row in rows]
